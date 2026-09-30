#!/usr/bin/env python3
"""Tiny calendar CLI over synthetic JSON data. Used by the meeting-scheduler skill.

Commands:
  contacts                              list known people
  list  [--who NAME] [--from D] [--to D] list events (default: primary user, next 14 days)
  free  --with NAME[,NAME] --date YYYY-MM-DD [--duration MIN] [--earliest HH:MM] [--latest HH:MM]
                                        slots where the primary user and all named people are free
  book  --title T --with NAME[,NAME] --start ISO --end ISO [--location L]
                                        add an event to every attendee's calendar (refuses on conflict)
  cancel --id EVT_ID                    remove an event
All output is JSON.
"""
import argparse, json, os, sys, uuid
from datetime import datetime, timedelta, date

DATA_DIR = os.environ.get("CAPSTONE_CAL_DATA") or os.path.join(os.path.expanduser("~"), ".openclaw", "workspace", "data")
CAL = os.path.join(DATA_DIR, "calendar.json")
CONTACTS = os.path.join(DATA_DIR, "contacts.json")

def load(p):
    with open(p) as f: return json.load(f)
def save(p, d):
    with open(p, "w") as f: json.dump(d, f, indent=2, ensure_ascii=False); f.write("\n")
def dt(s): return datetime.fromisoformat(s)
def out(o): print(json.dumps(o, indent=2, ensure_ascii=False))

def resolve(names, contacts):
    people = [contacts["primary_user"]] + contacts["contacts"]
    found = []
    for n in names:
        n = n.strip().lower()
        m = [p for p in people if p["name"].lower() == n or p["name"].lower().split()[0] == n]
        if not m: sys.exit(json.dumps({"error": f"unknown person: {n}", "known": [p["name"] for p in people]}))
        found.append(m[0]["name"])
    return found

def busy_for(person, events):
    return [e for e in events if person in e["attendees"]]

def overlaps(a0, a1, b0, b1): return a0 < b1 and b0 < a1

def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("contacts")
    p = sub.add_parser("list"); p.add_argument("--who"); p.add_argument("--from", dest="frm"); p.add_argument("--to")
    p = sub.add_parser("free"); p.add_argument("--with", dest="with_", required=True); p.add_argument("--date", required=True)
    p.add_argument("--duration", type=int, default=30); p.add_argument("--earliest", default="09:00"); p.add_argument("--latest", default="18:00")
    p = sub.add_parser("book"); p.add_argument("--title", required=True); p.add_argument("--with", dest="with_", required=True)
    p.add_argument("--start", required=True); p.add_argument("--end", required=True); p.add_argument("--location", default="Zoom")
    p = sub.add_parser("cancel"); p.add_argument("--id", required=True)
    a = ap.parse_args()

    contacts = load(CONTACTS); cal = load(CAL); events = cal["events"]; me = contacts["primary_user"]["name"]

    if a.cmd == "contacts":
        out({"primary_user": contacts["primary_user"], "contacts": contacts["contacts"]})
    elif a.cmd == "list":
        who = resolve([a.who], contacts)[0] if a.who else me
        f = dt(a.frm) if a.frm else datetime.combine(date.today(), datetime.min.time())
        t = dt(a.to) if a.to else f + timedelta(days=14)
        ev = [e for e in busy_for(who, events) if overlaps(dt(e["start"]), dt(e["end"]), f, t)]
        out({"person": who, "from": f.isoformat(), "to": t.isoformat(), "events": sorted(ev, key=lambda e: e["start"])})
    elif a.cmd == "free":
        people = [me] + resolve(a.with_.split(","), contacts)
        day = date.fromisoformat(a.date)
        lo = datetime.combine(day, datetime.strptime(a.earliest, "%H:%M").time())
        hi = datetime.combine(day, datetime.strptime(a.latest, "%H:%M").time())
        busy = [(dt(e["start"]), dt(e["end"])) for p in people for e in busy_for(p, events)]
        slots = []; cur = lo; step = timedelta(minutes=15); dur = timedelta(minutes=a.duration)
        while cur + dur <= hi:
            if not any(overlaps(cur, cur + dur, b0, b1) for b0, b1 in busy):
                slots.append({"start": cur.isoformat(timespec="minutes"), "end": (cur + dur).isoformat(timespec="minutes")})
            cur += step
        # merge adjacent slots into windows for readability
        windows = []
        for s in slots:
            if windows and windows[-1]["end"] >= s["start"]:
                windows[-1]["end"] = s["end"]
            else:
                windows.append(dict(s))
        out({"date": a.date, "people": people, "duration_min": a.duration, "free_windows": windows,
             "busy": sorted([{"who": p, "title": e["title"], "start": e["start"], "end": e["end"]} for p in people for e in busy_for(p, events) if dt(e["start"]).date() == day], key=lambda x: x["start"])})
    elif a.cmd == "book":
        people = [me] + resolve(a.with_.split(","), contacts)
        s, e = dt(a.start), dt(a.end)
        if e <= s: sys.exit(json.dumps({"error": "end must be after start"}))
        conflicts = [{"who": p, "title": ev["title"], "start": ev["start"], "end": ev["end"]} for p in people for ev in busy_for(p, events) if overlaps(s, e, dt(ev["start"]), dt(ev["end"]))]
        if conflicts: sys.exit(json.dumps({"error": "conflict", "conflicts": conflicts}))
        ev = {"id": "evt-" + uuid.uuid4().hex[:6], "owner": me, "title": a.title, "start": s.isoformat(timespec="minutes"), "end": e.isoformat(timespec="minutes"), "attendees": people, "location": a.location, "created_by": "openclaw-meeting-scheduler"}
        events.append(ev); save(CAL, cal); out({"booked": ev})
    elif a.cmd == "cancel":
        before = len(events); cal["events"] = [x for x in events if x["id"] != a.id]
        if len(cal["events"]) == before: sys.exit(json.dumps({"error": f"no event {a.id}"}))
        save(CAL, cal); out({"cancelled": a.id})

if __name__ == "__main__": main()
