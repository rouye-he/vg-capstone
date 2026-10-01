#!/usr/bin/env python3
"""Per-user Gmail read-only access for the assistant. Each requester authorises their own Google account;
tokens are stored per requester handle and never shared. JSON out.

  status      --user +1555...                       is this requester connected?
  auth-url    --user +1555...                       start OAuth: prints the Google consent URL to send to the user
  connect     --user +1555... --redirect-url URL    finish OAuth with the redirect URL (contains code=)
  fetch       --user +1555... [--limit 50] [--query 'newer_than:30d']
                                                    last N messages with a suggested category
  disconnect  --user +1555...                       delete the stored token

Setup by the owner (once): put a Google OAuth *Desktop app* client file at ~/.openclaw/google/client_secret.json
with the Gmail API enabled and the users' addresses added as test users (see openclaw-workspace/README.md).
"""

import argparse
import base64
import hashlib
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HOME = os.path.expanduser("~")
GDIR = os.environ.get("CAPSTONE_GOOGLE_DIR") or os.path.join(HOME, ".openclaw", "google")
CLIENT = os.path.join(GDIR, "client_secret.json")
TOKENS = os.path.join(GDIR, "tokens")
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
REDIRECT = "http://localhost:8765/"  # no server listens; the user copies the URL they land on
AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
API = "https://gmail.googleapis.com/gmail/v1/users/me"


def out(o, code=0):
    print(json.dumps(o, indent=2, ensure_ascii=False))
    sys.exit(code)


def safe_user(u):
    u = (u or "").strip()
    if not re.fullmatch(r"[+\w.@-]{3,80}", u):
        out({"error": "bad --user handle"}, 2)
    return u


def tpath(u):
    return os.path.join(TOKENS, re.sub(r"[^\w.@+-]", "_", u) + ".json")


def ppath(u):
    return os.path.join(TOKENS, re.sub(r"[^\w.@+-]", "_", u) + ".pending.json")


def client():
    try:
        with open(CLIENT) as f:
            c = json.load(f)
    except FileNotFoundError:
        out({"error": "not_configured", "detail": f"owner must place a Google OAuth client file at {CLIENT}"}, 3)
    c = c.get("installed") or c.get("web") or c
    return c["client_id"], c.get("client_secret", "")


def write_private(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(d, f)
    os.chmod(p, 0o600)


def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:400]
        out({"error": f"http_{e.code}", "detail": body}, 4)


def cmd_status(a):
    u = safe_user(a.user)
    if not os.path.exists(CLIENT):
        out(
            {
                "user": u,
                "configured": False,
                "connected": False,
                "detail": "owner has not configured the Google OAuth client yet",
            }
        )
    t = os.path.exists(tpath(u))
    out({"user": u, "configured": True, "connected": t, "email": json.load(open(tpath(u))).get("email") if t else None})


def cmd_auth_url(a):
    u = safe_user(a.user)
    cid, _ = client()
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    write_private(ppath(u), {"verifier": verifier, "state": state, "created": time.time()})
    q = {
        "client_id": cid,
        "redirect_uri": REDIRECT,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    out(
        {
            "user": u,
            "auth_url": AUTH + "?" + urllib.parse.urlencode(q),
            "instructions": (
                "Open the link, choose the Google account, allow read-only Gmail access. The browser then "
                "tries to open localhost and shows an error page; copy that page's full address "
                "(it starts with http://localhost:8765/?code=) and send it back here."
            ),
        }
    )


def cmd_connect(a):
    u = safe_user(a.user)
    cid, csec = client()
    try:
        pend = json.load(open(ppath(u)))
    except FileNotFoundError:
        out({"error": "no_pending_auth", "detail": "run auth-url first"}, 5)
    if time.time() - pend["created"] > 900:
        out({"error": "auth_expired", "detail": "start again with auth-url"}, 5)
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(a.redirect_url.strip()).query)
    code = (qs.get("code") or [None])[0]
    state = (qs.get("state") or [None])[0]
    if not code:
        out({"error": "no_code_in_url"}, 5)
    if state != pend["state"]:
        out({"error": "state_mismatch"}, 5)
    data = urllib.parse.urlencode(
        {
            "client_id": cid,
            "client_secret": csec,
            "code": code,
            "code_verifier": pend["verifier"],
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT,
        }
    ).encode()
    tok = http(TOKEN, data, {"Content-Type": "application/x-www-form-urlencoded"})
    tok["obtained"] = time.time()
    prof = http(API + "/profile", headers={"Authorization": "Bearer " + tok["access_token"]})
    tok["email"] = prof.get("emailAddress")
    write_private(tpath(u), tok)
    os.remove(ppath(u))
    out({"user": u, "connected": True, "email": tok["email"], "scope": "gmail.readonly"})


def access_token(u):
    try:
        tok = json.load(open(tpath(u)))
    except FileNotFoundError:
        out({"error": "not_connected", "detail": "ask the user to connect their Gmail first (auth-url)"}, 6)
    if time.time() - tok.get("obtained", 0) > tok.get("expires_in", 3600) - 60:
        cid, csec = client()
        data = urllib.parse.urlencode(
            {
                "client_id": cid,
                "client_secret": csec,
                "refresh_token": tok["refresh_token"],
                "grant_type": "refresh_token",
            }
        ).encode()
        new = http(TOKEN, data, {"Content-Type": "application/x-www-form-urlencoded"})
        tok.update(new)
        tok["obtained"] = time.time()
        write_private(tpath(u), tok)
    return tok["access_token"]


RULES = [
    ("finance", r"invoice|receipt|payment|billing|statement|refund|purchase|order (confirmation|#)|paid|due"),
    ("meetings", r"invitation|meeting|calendar|zoom|teams|accepted:|declined:|reschedul"),
    ("security", r"verification code|verify your|password|sign-in|login|2fa|security alert|new device"),
    ("recruiting_hr", r"interview|offer|application|recruit|onboarding|payroll|benefits|hr "),
    ("newsletters", r"newsletter|digest|unsubscribe|weekly|roundup|% off|sale|deal|promo|webinar"),
]


def suggest(subject, snippet, labels):
    text = f"{subject} {snippet}".lower()
    if "CATEGORY_PROMOTIONS" in labels:
        return "promotions"
    if "CATEGORY_SOCIAL" in labels:
        return "social"
    for name, rx in RULES:
        if re.search(rx, text):
            return name
    if "CATEGORY_UPDATES" in labels:
        return "updates"
    if "CATEGORY_FORUMS" in labels:
        return "forums"
    return "personal_or_work"


def cmd_fetch(a):
    u = safe_user(a.user)
    at = access_token(u)
    h = {"Authorization": "Bearer " + at}
    q = {"maxResults": max(1, min(a.limit, 100))}
    if a.query:
        q["q"] = a.query
    lst = http(API + "/messages?" + urllib.parse.urlencode(q), headers=h)
    msgs = []
    for m in lst.get("messages", []):
        d = http(
            API
            + f"/messages/{m['id']}?format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date",
            headers=h,
        )
        hd = {x["name"]: x["value"] for x in d.get("payload", {}).get("headers", [])}
        labels = d.get("labelIds", [])
        msgs.append(
            {
                "id": m["id"],
                "date": hd.get("Date", ""),
                "from": hd.get("From", ""),
                "subject": hd.get("Subject", ""),
                "snippet": d.get("snippet", "")[:160],
                "unread": "UNREAD" in labels,
                "gmail_category": next(
                    (lab.split("_", 1)[1].lower() for lab in labels if lab.startswith("CATEGORY_")), None
                ),
                "suggested_category": suggest(hd.get("Subject", ""), d.get("snippet", ""), labels),
            }
        )
    counts = {}
    for x in msgs:
        counts[x["suggested_category"]] = counts.get(x["suggested_category"], 0) + 1
    out(
        {
            "user": u,
            "email": json.load(open(tpath(u))).get("email"),
            "count": len(msgs),
            "suggested_counts": counts,
            "messages": msgs,
        }
    )


def cmd_disconnect(a):
    u = safe_user(a.user)
    for p in (tpath(u), ppath(u)):
        if os.path.exists(p):
            os.remove(p)
    out({"user": u, "connected": False})


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("status", "auth-url", "disconnect"):
        p = sub.add_parser(name)
        p.add_argument("--user", required=True)
    p = sub.add_parser("connect")
    p.add_argument("--user", required=True)
    p.add_argument("--redirect-url", required=True)
    p = sub.add_parser("fetch")
    p.add_argument("--user", required=True)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--query")
    a = ap.parse_args()
    {
        "status": cmd_status,
        "auth-url": cmd_auth_url,
        "connect": cmd_connect,
        "fetch": cmd_fetch,
        "disconnect": cmd_disconnect,
    }[a.cmd](a)


if __name__ == "__main__":
    main()
