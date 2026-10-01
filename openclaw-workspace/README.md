# OpenClaw workspace add-ons: identity isolation, role skills, synthetic data

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

## Identity isolation (role-based access over iMessage)

The sender's iMessage handle (phone number) is the identity. It comes from the channel adapter, never from message text, so it cannot be spoofed by typing "I am the CFO".

| Layer | Mechanism | Effect |
| --- | --- | --- |
| 1 Authentication | `channels.imessage.dmPolicy: allowlist` + `accessGroups.employees` | Numbers not on the roster are dropped before any model call. No reply, no tokens spent |
| 2 Authorization | `bindings`: phone -> agent. Agents = roles (`eng`, `finance`, `ops`, `guest`, `main`), each with its own workspace, English role prompt (`SOUL.md`) and `skills` allowlist | A Finance person's bot has the ledger skill and not GitHub; Engineering has GitHub and not the ledger |
| 3 Defense in depth | `tools.toolsBySender` and `agents.entries.guest.tools.deny` | The guest cannot `exec` at all, even if a prompt tricks the model |
| Sessions | `session.dmScope: per-peer` | Every person has a private conversation, even within the same role |

Agents scale with roles, not people: 10 engineers and 10 finance staff are still 2 agents. Skills exist once in `~/.openclaw/skills/`; a role only lists which names it may use.

Files:

| Path | What it is |
| --- | --- |
| `roles/roster.json` | Source of truth: name, phone, role per person. Edit this to add people or swap in real numbers |
| `roles/gen_config.py` | Role table (role -> skills, tool denies). Generates `openclaw.roles.json5` from the roster |
| `roles/apply.sh` | Installs skills, data and role workspaces, regenerates and applies the config, prints the routing table |
| `workspaces/<role>/SOUL.md` | Role prompt: who the requester is, what the bot may and may not do for them, English only |
| `skills/expense-ledger/` | Finance skill over `data/invoices.json`: list, show, summary, approve, reject |

Role table today:

| Role | Who (roster) | Skills |
| --- | --- | --- |
| main (owner) | Richard, not routable over iMessage while his own Apple ID hosts the bot | all |
| eng | Alex, Sam | github, meeting-scheduler, weather |
| finance | Priya, Mei | expense-ledger, meeting-scheduler (availability only), weather |
| ops | Rouye | meeting-scheduler (may book), apple-reminders, weather |
| guest | Indepal, and any admitted number without a binding | weather only, no exec / fs |

### Isolation test results (2026-09-30, local agent turns)

| # | Agent | Request | Result |
| --- | --- | --- | --- |
| A | guest | List open GitHub issues in openclaw/openclaw, and the weather in Pittsburgh | Weather answered (70°F, cloudy). GitHub refused: "only for Enterprise Team employees", pointed to a staff member. No shell command run |
| B | finance | Show pending invoices and approve INV-1003 | Listed 3 pending with amounts, approved INV-1003 with `--by "Priya Nair"`, ledger file updated, others left pending |

Caveat: with the `claude-cli` runtime the model process has native tools; skill allowlists are a visibility filter and `tools.deny` is enforced on native calls by OpenClaw's canonical policy. For a production bot, add per-agent exec allowlists (`openclaw approvals`) or the sandbox. GitHub skill needs `gh auth login` on this Mac before Engineering can use it; apple-reminders needs the Reminders permission prompt on first use.
