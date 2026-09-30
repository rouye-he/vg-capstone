---
name: meeting-scheduler
description: Check availability and book meetings on the primary user's calendar with known contacts (synthetic capstone calendar).
---
# Meeting scheduler

You manage the primary user's calendar through the CLI at `{baseDir}/scripts/calendar_tool.py`. All calendars are synthetic capstone test data. Run it with the `exec` tool, always with `python3`:

```bash
python3 {baseDir}/scripts/calendar_tool.py contacts
python3 {baseDir}/scripts/calendar_tool.py list --who "Alex Chen" --from 2026-10-06T00:00 --to 2026-10-07T00:00
python3 {baseDir}/scripts/calendar_tool.py free --with "Alex Chen" --date 2026-10-06 --duration 30
python3 {baseDir}/scripts/calendar_tool.py book --title "Phase 1 architecture" --with "Alex Chen" --start 2026-10-06T15:00 --end 2026-10-06T15:30
python3 {baseDir}/scripts/calendar_tool.py cancel --id evt-abc123
```

## Procedure

1. Resolve people with `contacts` if you are unsure of a name. Use full names in `--with`.
2. Work out the date from the user's words. "Next Tuesday" means the first Tuesday after today. Today's date comes from the runtime context.
3. Run `free` for that date. Never guess availability; only propose windows the tool returns.
4. If the user gave a specific time and it is free, `book` it. If the user only gave a rough preference ("afternoon"), pick the earliest matching free window and `book` it, then say which window you chose and offer to move it.
5. If `book` returns `conflict`, do not retry blindly. Report the conflict and propose the next free windows from `free`.
6. Reply with a short confirmation: title, date, time range, attendees, and the event id. One or two sentences.

## Rules

- Book only with names present in `contacts`. If a requested person is unknown, ask the user rather than inventing a contact.
- Only the primary user (the account owner) may book or cancel. If the request clearly comes from someone else on the primary user's behalf, propose times but say that the owner must confirm before booking.
- Do not create events outside 09:00-18:00 local time unless the user explicitly asks.
- Do not read or modify anything except through this tool.
