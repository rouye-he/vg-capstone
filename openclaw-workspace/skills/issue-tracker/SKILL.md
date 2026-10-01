---
name: issue-tracker
description: List, inspect, create, assign, comment on and close engineering issues in the team issue tracker (synthetic GitHub stand-in).
---
# Issue tracker

Use the `exec` tool to run `python3 {baseDir}/scripts/issues_tool.py` with one of: `list [--status open] [--assignee NAME] [--label L]`, `show --id 101`, `create --title "..." [--body "..."] [--priority P1|P2|P3] [--labels a,b] [--assignee NAME]`, `assign --id 101 --to NAME`, `comment --id 101 --by NAME --text "..."`, `close --id 101 --by NAME`. Output is JSON. When the user says "GitHub issues", this tracker is what they mean.

## Rules

- Only Engineering-role requesters may create, assign, comment or close. Use the requester's name for `--by`.
- Summarise lists as "#id title (priority, assignee)". Keep replies to one to three sentences.
- Do not invent issues. If an id is unknown, say so.
