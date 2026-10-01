#!/usr/bin/env python3
"""Tiny expense ledger CLI over synthetic JSON data. Used by the expense-ledger skill.
  list [--status pending|approved|rejected]   list invoices
  show --id INV-1002                           one invoice
  approve --id INV-1002 --by "Priya Nair"      mark approved
  reject  --id INV-1002 --by "Priya Nair" --reason "..."
  summary                                      totals by status
All output is JSON.
"""
import argparse, json, os, sys
DATA_DIR = os.environ.get("CAPSTONE_CAL_DATA") or os.path.join(os.path.expanduser("~"), ".openclaw", "workspace", "data")
P = os.path.join(DATA_DIR, "invoices.json")
def load():
    with open(P) as f: return json.load(f)
def save(d):
    with open(P, "w") as f: json.dump(d, f, indent=2); f.write("\n")
def out(o): print(json.dumps(o, indent=2))
def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("--status")
    p = sub.add_parser("show"); p.add_argument("--id", required=True)
    p = sub.add_parser("approve"); p.add_argument("--id", required=True); p.add_argument("--by", required=True)
    p = sub.add_parser("reject"); p.add_argument("--id", required=True); p.add_argument("--by", required=True); p.add_argument("--reason", required=True)
    sub.add_parser("summary")
    a = ap.parse_args(); d = load(); inv = d["invoices"]
    def get(i):
        m = [x for x in inv if x["id"] == i]
        if not m: sys.exit(json.dumps({"error": f"no invoice {i}"}))
        return m[0]
    if a.cmd == "list": out([x for x in inv if not a.status or x["status"] == a.status])
    elif a.cmd == "show": out(get(a.id))
    elif a.cmd in ("approve", "reject"):
        x = get(a.id)
        if x["status"] != "pending": sys.exit(json.dumps({"error": f"{a.id} is already {x['status']}"}))
        x["status"] = "approved" if a.cmd == "approve" else "rejected"; x["approved_by"] = a.by
        if a.cmd == "reject": x["memo"] += f" (rejected: {a.reason})"
        save(d); out({a.cmd + "d": x})
    elif a.cmd == "summary":
        s = {}
        for x in inv: s.setdefault(x["status"], {"count": 0, "total_usd": 0.0}); s[x["status"]]["count"] += 1; s[x["status"]]["total_usd"] += x["amount_usd"]
        out(s)
if __name__ == "__main__": main()
