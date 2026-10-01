---
name: expense-ledger
description: List, inspect, approve or reject vendor invoices in the company expense ledger (synthetic capstone data).
---
# Expense ledger

Use the `exec` tool to run `python3 {baseDir}/scripts/ledger_tool.py` with one of: `list [--status pending]`, `show --id INV-1002`, `summary`, `approve --id INV-1002 --by "<approver full name>"`, `reject --id INV-1002 --by "<approver>" --reason "<why>"`. Output is JSON.

## Rules

- Only a Finance-role requester may approve or reject. Use the requester's name from your role instructions as `--by`. Never approve on behalf of someone else.
- Before approving, `show` the invoice and state vendor, amount and memo in your reply.
- Do not invent invoices. If an id is unknown, say so.
- Keep replies to one to three sentences. Amounts in USD with two decimals.
