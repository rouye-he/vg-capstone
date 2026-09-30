# iMessage Workstream — Handoff

**From:** Rouye He · **As of:** 2026-09-30 · **Project:** CMU × Virtual Gold Enterprise AI Capstone

> **Update 2026-09-30 (Richard):** TC-06 to TC-10 and raw-event mode are done (10/10 scenarios, 22 tests). A second real-Mac environment is installed and configured, see `openclaw-imessage-runbook.md`. Current checklist, sponsor questions and a reply draft are in `PHASE1_STATUS.md`.

## Status in one line

Research is done, the iMessage Simulator runs with 5/5 scenarios passing, and a real-device deployment on a Mac is set up except for one blocker: the new Apple ID cannot yet activate iMessage.

## What's in this package

| Item | What it is |
| --- | --- |
| `iMessage_Integration_Design.pdf` | Design doc: feasibility, integration options compared, how OpenClaw channels work, MessageEnvelope v0.1, Simulator design, real-Mac deployment log, risks and open questions, sources |
| `imessage-simulator/` | Working code: JSON Schemas, channel ingress, mock assistant, scenario runner, raw-event mode, TC-01 to TC-10, unit tests |
| `openclaw-imessage-runbook.md` | Exact install and config steps run on Richard's Mac, and the manual steps that remain |
| `PHASE1_STATUS.md` | Checklist against the sponsor's Phase 1 ask, security controls, questions for VG, reply draft |
| `openclaw-workspace/` | Meeting-scheduler skill and synthetic contacts/calendars for demos, with test results |
| `HANDOFF.md` | This file |

## Key findings

1. **OpenClaw already ships an official iMessage channel** (`@openclaw/imessage`, built on the `imsg` CLI). The work is deployment and integration, not a new build. This contradicts what was said in the 9/21 meeting and should be confirmed with Aarvin.
2. **Deployment requirements, verified on a real Mac:**
   - macOS 14 Sonoma or later (`imsg` 0.15.9 refuses to install on macOS 13)
   - After a major macOS upgrade, Command Line Tools must be updated before Homebrew will build
   - A dedicated macOS user and a dedicated Apple ID for the assistant (keeps the bot away from personal messages)
   - Full Disk Access + Automation permissions for the process running `imsg`
   - No SIP changes needed for text and attachments
3. **Open blocker:** the new Apple ID (`vgcapstonebot@gmail.com`) signs in to FaceTime but not iMessage; the login window closes without completing sign-in, and no `chat.db` is created. System logs show no registration error. Likely a new-account activation restriction on Apple's side. Next step: retry after 24–48 hours, then contact Apple Support. Full step-by-step log and evidence: the **Deployment log** section of the design PDF (pages 9–10).

## Run the Simulator (about 2 minutes)

```bash
cd imessage-simulator
python3 -m venv .venv
source .venv/bin/activate
pip install pyyaml jsonschema pytest
python -m imsg_sim.runner     # expect: 10/10 scenarios passed
python -m pytest -q           # expect: 22 passed
```

No Mac, Apple account or client data needed. All data is synthetic (555 phone numbers, a made-up invoice).

## Suggested next steps

- [ ] Retry iMessage sign-in on the bot account; once `chat.db` exists, run `imsg chats --limit 5`
- [x] Add TC-06 to TC-10 (echo loop, unknown sender, group chat, split-send, HEIC)
- [x] Raw-event mode for real `imsg` output
- [x] Local git repo initialised (push to the team org still needed)
- [ ] Ask Virtual Gold the three open questions:
  1. Does your IAM layer run inside OpenClaw, or in your own channel adapters?
  2. Which OpenClaw version does VG08 run, and is the gateway on a Linux VM or a Mac?
  3. Can VG provide a dedicated Mac and Apple ID for the assistant?

## Notes

- Nothing here contains client code or data; the NDA is not yet signed.
- The design doc and slides also exist as live online versions; ask Rouye for access if you want to comment or edit.
