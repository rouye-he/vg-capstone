#!/usr/bin/env python3
"""Tiny issue tracker CLI over synthetic JSON (GitHub stand-in). JSON out.
  list [--status open|closed] [--assignee NAME] [--label L]
  show --id 101
  create --title T [--body B] [--priority P1|P2|P3] [--labels a,b] [--assignee NAME]
  assign --id 101 --to NAME
  comment --id 101 --by NAME --text T
  close --id 101 --by NAME
"""
import argparse, json, os, sys, datetime
DATA_DIR = os.environ.get("CAPSTONE_CAL_DATA") or os.path.join(os.path.expanduser("~"), ".openclaw", "workspace", "data")
P = os.path.join(DATA_DIR, "issues.json")
def load():
    with open(P) as f: return json.load(f)
def save(d):
    with open(P, "w") as f: json.dump(d, f, indent=2, ensure_ascii=False); f.write("\n")
def out(o): print(json.dumps(o, indent=2, ensure_ascii=False))
def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("--status"); p.add_argument("--assignee"); p.add_argument("--label")
    p = sub.add_parser("show"); p.add_argument("--id", type=int, required=True)
    p = sub.add_parser("create"); p.add_argument("--title", required=True); p.add_argument("--body", default=""); p.add_argument("--priority", default="P3"); p.add_argument("--labels", default=""); p.add_argument("--assignee")
    p = sub.add_parser("assign"); p.add_argument("--id", type=int, required=True); p.add_argument("--to", required=True)
    p = sub.add_parser("comment"); p.add_argument("--id", type=int, required=True); p.add_argument("--by", required=True); p.add_argument("--text", required=True)
    p = sub.add_parser("close"); p.add_argument("--id", type=int, required=True); p.add_argument("--by", required=True)
    a = ap.parse_args(); d = load(); iss = d["issues"]
    def get(i):
        m = [x for x in iss if x["id"] == i]
        if not m: sys.exit(json.dumps({"error": f"no issue #{i}"}))
        return m[0]
    today = datetime.date.today().isoformat()
    if a.cmd == "list":
        r = [x for x in iss if (not a.status or x["status"] == a.status) and (not a.assignee or (x.get("assignee") or "").lower().startswith(a.assignee.lower())) and (not a.label or a.label in x["labels"])]
        out({"repo": d["repo"], "count": len(r), "issues": [{k: x[k] for k in ("id", "title", "status", "priority", "assignee", "labels")} for x in r]})
    elif a.cmd == "show": out(get(a.id))
    elif a.cmd == "create":
        n = max(x["id"] for x in iss) + 1
        x = {"id": n, "title": a.title, "status": "open", "priority": a.priority, "assignee": a.assignee, "labels": [l for l in a.labels.split(",") if l], "created": today, "body": a.body, "comments": []}
        iss.append(x); save(d); out({"created": x})
    elif a.cmd == "assign":
        x = get(a.id); x["assignee"] = a.to; save(d); out({"assigned": {"id": x["id"], "assignee": x["assignee"]}})
    elif a.cmd == "comment":
        x = get(a.id); x.setdefault("comments", []).append({"by": a.by, "date": today, "text": a.text}); save(d); out({"commented": x["id"], "comments": len(x["comments"])})
    elif a.cmd == "close":
        x = get(a.id)
        if x["status"] == "closed": sys.exit(json.dumps({"error": f"#{a.id} already closed"}))
        x["status"] = "closed"; x.setdefault("comments", []).append({"by": a.by, "date": today, "text": "closed"}); save(d); out({"closed": x["id"]})
if __name__ == "__main__": main()
