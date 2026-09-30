# OpenClaw workspace add-ons: meeting scheduler with synthetic data

Files here are copied into `~/.openclaw/workspace/` on the gateway Mac. They give the assistant one concrete capability to exercise over iMessage: checking availability and booking meetings. All data is synthetic (555 numbers, example.com emails, invented calendars).

| Path | What it is |
| --- | --- |
| `data/contacts.json` | Primary user plus 5 contacts with role, relationship (`teammate` / `external`) and timezone |
| `data/calendar.json` | Events for the week of 2026-10-05 for Richard, Alex, Aarvin, Rouye |
| `skills/meeting-scheduler/SKILL.md` | Skill instructions: resolve names, run `free`, book only free slots, report conflicts, owner-only booking |
| `skills/meeting-scheduler/scripts/calendar_tool.py` | CLI: `contacts`, `list`, `free`, `book` (refuses on conflict), `cancel`. JSON in, JSON out |

## Install

```bash
mkdir -p ~/.openclaw/workspace/skills ~/.openclaw/workspace/data
cp -R skills/meeting-scheduler ~/.openclaw/workspace/skills/
cp data/*.json ~/.openclaw/workspace/data/
openclaw skills list | grep meeting-scheduler     # expect: ready
```

To reset the calendar after a demo, copy `data/calendar.json` again.

## Test results (2026-09-30, local agent turns, Claude Max login via claude-cli runtime)

| # | Request (as primary user) | Expected | Result |
| --- | --- | --- | --- |
| 1 | 帮我和 Alex 约下周二下午一个 30 分钟的会，主题是 Phase 1 architecture | Pick earliest afternoon slot free for both (15:00) and book | Booked `evt-1e488b` 2026-10-06 15:00–15:30, attendees Richard + Alex |
| 2 | 下周二下午 2 点和 Alex 开个 30 分钟的会，聊 Phase 2 goals | 14:00 conflicts with Richard's office hours: refuse, propose alternatives, do not book | Not booked. Reply named the conflict, proposed 15:30–16:00 and 17:00–18:00, asked for confirmation |

Reproduce:

```bash
openclaw agent --local --agent main --session-id demo-1 --message "帮我和 Alex 约下周二下午一个 30 分钟的会，主题是 Phase 1 architecture。" --json
python3 -c "import json;print([e for e in json.load(open('$HOME/.openclaw/workspace/data/calendar.json'))['events'] if e.get('created_by')])"
```

Observation: the assistant answered in English to a Chinese request. Add a language directive to `USER.md` or `SOUL.md` if the demo should be in Chinese.

## Next for Phase 2

- Same skill over iMessage: a teammate texts "can Richard do Tuesday 3pm?" and the assistant answers from the calendar without booking (owner-only rule in the skill).
- Replace the JSON files with a real calendar (Google Calendar via OpenClaw's bundled skill) once VG confirms which accounts the fictional org will use.
