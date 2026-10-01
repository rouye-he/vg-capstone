# VG Capstone: Enterprise AI Assistant

CMU MISM capstone with Virtual Gold. Private repo; synthetic data only, no client code or data.

## Repository map

| Path | What it is | Owner |
| --- | --- | --- |
| `iMessage_Integration_Design.pdf` | Design doc: feasibility, integration options, MessageEnvelope v0.1, Simulator, deployment log | Rouye |
| `imessage-simulator/` | iMessage channel contract and Simulator: schemas, ingress, mock assistant, scenarios TC-01 to TC-10, raw-event mode, tests | Rouye, Richard |
| `openclaw-workspace/` | Running OpenClaw over iMessage with identity isolation: roster-driven role config, five role prompts, four demo skills (meeting scheduler, expense ledger, issue tracker, Gmail digest) on synthetic data | Richard |
| `openclaw-imessage-runbook.md` | Everything run on the gateway Mac: install, config, permissions, real-device tests, the OpenClaw 2026.9.7 reply bug and its workaround | Richard |
| `PHASE1_STATUS.md` | Checklist against the sponsor's Phase 1 ask, security controls, open questions for VG, reply draft | Richard |
| `HANDOFF.md` | Where things stand and how to pick them up | Rouye, Richard |

## Quick start

Simulator (no Mac or Apple account needed):

```bash
cd imessage-simulator
python3 -m venv .venv && source .venv/bin/activate
pip install pyyaml jsonschema pytest
python -m imsg_sim.runner      # expect 10/10 scenarios passed
python -m pytest -q            # expect 22 passed
```

Real device (a Mac with Messages signed in): follow `openclaw-imessage-runbook.md`, then `openclaw-workspace/README.md` for roles and skills. The iMessage channel is shipped **disabled** (`IMESSAGE_ENABLED = False` in `openclaw-workspace/roles/gen_config.py`); flip it to `True`, run `roles/apply.sh` and start `openclaw gateway` when you want the bot live.

## Status (2026-09-30)

- Phase 1 real-device test done: a Finance-role tester and an Engineering-role tester each got role-appropriate answers and refusals over iMessage; an unknown number got one pairing notice and nothing else. Details in `PHASE1_STATUS.md` and the runbook.
- Known upstream issue: OpenClaw 2026.9.7 cannot deliver automatic replies over iMessage (openclaw/openclaw #161976). Workaround in place: agents send replies explicitly with the `message` tool, locked to the current conversation.
- Gmail digest skill is implemented but not yet exercised; it needs a Google OAuth client file on the gateway Mac (see `openclaw-workspace/README.md`).

## Conventions

- Python: PEP 8, formatted with `black` and linted with `ruff` (settings in `pyproject.toml`, line length 120). Module docstrings describe each CLI's commands. Scripts print JSON and exit non-zero on error.
- Data: everything under `openclaw-workspace/data/` and `imessage-simulator/fixtures/` is invented (555 numbers, example.com addresses). Real phone numbers go in `roles/roster.local.json`, which is git-ignored, never in `roster.json`.
- Secrets: none in the repo. OAuth client files and tokens live under `~/.openclaw/google/` on the gateway Mac.
- Docs: one Markdown file per concern; update `PHASE1_STATUS.md` when a checklist item changes and the runbook when a command is run on the Mac.
