# Phase 1 status: secure iMessage channel to our own OpenClaw

**Updated:** 2026-09-30 by Richard (Xiuqi) Zhu, building on Rouye He's handoff of the same day.
**Sponsor ask (Aarvin, email):** experiment with a secure iMessage channel to our own OpenClaw instance, so the assistant can serve one primary user while safely interacting with others on their behalf. Bring findings and be ready for an architecture discussion.

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Research: does OpenClaw have an iMessage channel? | Done | Yes, official `@openclaw/imessage` on `imsg`. Design PDF section 2. Contradicts 9/21 meeting; raise with Aarvin. |
| 2 | Integration options compared, recommendation | Done | Design PDF section 3: prototype with A, decide A2 vs C after the IAM question |
| 3 | MessageEnvelope v0.1 contract | Done | `imessage-simulator/schemas/`. Two additive fields added today (see simulator README) |
| 4 | Simulator envelope mode, TC-01 to TC-05 | Done | 5/5 |
| 5 | TC-06 to TC-10 (echo, unknown sender, group, split-send, HEIC) | Done today | 10/10 scenarios, 22 unit tests |
| 6 | Simulator raw-event mode (real `imsg` JSON) | Done today | `imsg_sim/raw_events.py`, field names verified against the plugin source |
| 7 | Second real-Mac environment (Richard) | Installed and configured | `openclaw-imessage-runbook.md`; permissions granted, model runs on the Claude Max login via `claude-cli` runtime, gateway pairing test pending |
| 8 | Real-Mac environment (Rouye) | Blocked | New Apple ID will not activate iMessage; retry after 24 to 48 h, then Apple Support, or use an established Apple ID |
| 9 | First real message end to end through OpenClaw | Done 2026-09-30 | Classmate as Finance: 5 requests answered or refused per role over iMessage; unknown number ingested and ignored. Needed a workaround for an OpenClaw 2026.9.7 reply bug, see runbook |
| 10 | Code in a private team repo | Local git repo created | Remote push needs a team GitHub org / repo name |
| 11 | Questions to Virtual Gold | Drafted below | Send before the meeting |
| 12 | NDA | Open | Each member signs individually |
| 13 | One real capability to demo (meeting scheduling on synthetic data) | Done today | `openclaw-workspace/`: skill + calendar CLI, 2/2 scenarios (book free slot, refuse conflict) |
| 14 | Identity isolation: roster allowlist, phone -> role agent routing, per-role skills, per-sender tool denies, per-person sessions | Done today | `openclaw-workspace/roles/`, README section "Identity isolation", 2/2 tests (guest denied GitHub, finance approved invoice) |

## What "secure" means in this design, and what is already enforced

| Layer | Control | Where |
| --- | --- | --- |
| Who can reach the bot | `dmPolicy: pairing`, explicit approval per handle, 1 h expiry | OpenClaw channel config |
| No group exposure in MVP | `groupPolicy: disabled` | OpenClaw channel config |
| Loop protection | own-handle and `is_from_me` rows dropped | ingress + OpenClaw plugin |
| Replay protection | dedupe on Apple GUID, 24 h window; plugin journals GUIDs for 4 h across restarts | ingress + OpenClaw plugin |
| Attachment hygiene | allowlist of 8 types, 16 MB cap, by-reference only, sha256 recorded | ingress |
| Least privilege on the Mac | dedicated macOS user + dedicated Apple ID; Full Disk Access only for the gateway process; no SIP change | deployment pattern |
| Roles | channel never assigns a role, `actor_role: unresolved`; VG IAM decides principal / delegate / colleague / external | envelope contract |
| Chat cannot change config | `configWrites: false` | OpenClaw channel config |
| Logging | IDs, sizes, hashes, status only | raw-event mode default |

## Open questions for Virtual Gold (send before the meeting)

1. Does VG's identity and permission logic run inside OpenClaw, or in your own channel adapters like the Gmail intake? If it is in the adapter, OpenClaw's built-in iMessage channel would bypass it and we should build Option C instead of A2.
2. Which OpenClaw version does VG08 run, and is the gateway on a Linux VM or a Mac? The iMessage plugin only works with a Mac in the loop.
3. Can VG provide, or approve us buying, a dedicated Mac (a Mac mini is enough) and a dedicated Apple ID for the assistant? A brand-new Apple ID may take days to activate iMessage; an established one avoids that.
4. Would the client accept a hosted iMessage relay (Option B) as fallback, given every executive message would pass through a third party?
5. Group chats: MVP is DMs only. Should the assistant ever answer in groups?
6. New from today: how was the Gmail channel's "primary user vs. other people" behaviour specified? We would like to mirror the same role vocabulary in MessageEnvelope.

## Draft reply to Aarvin

> Hi Aarvin,
>
> Thanks for the note. For Phase 1 we have started the iMessage experiment and have findings to discuss:
>
> - OpenClaw ships an official iMessage channel (`@openclaw/imessage`, built on the `imsg` CLI). We have it installed and configured on two of our Macs; the remaining step is a signed-in Apple ID for the assistant, which is blocked by Apple's activation delay for new accounts.
> - We have a MessageEnvelope contract and a simulator (10 scenarios, replayable without a Mac) covering attachments, dedupe, echo loops, unknown senders and group chats, plus a raw-event mode that consumes real `imsg` output.
> - The architecture decision we need your input on is where VG's identity layer lives (inside OpenClaw vs. in your channel adapters, as with Gmail). That decides between running the official plugin against a remote Mac and building an adapter that mirrors the Gmail intake. Full question list attached.
>
> For Phase 2, one suggestion for a collective goal: run a two-week "vendor onboarding" cycle for a fictional company, where each member's assistant handles a slice (intake over iMessage, document review, scheduling, approvals) and we measure how often the assistant needed the primary user to intervene.
>
> We will sign the NDA this week. Could we get 45 minutes with you [propose 2 to 3 slots]?
>
> Best,
> [name]

## Phase 2 priming (from the email)

Each member will get an assistant and act as a member of a fictional organization. Things to prepare as a primary user: a written behaviour expectation (what the assistant may do alone, what needs confirmation, what it must never do), a short list of evaluation criteria (interventions per task, errors caught, time saved), and the iMessage allowlist for that persona. The MessageEnvelope `kind` values (`ack`, `result`, `confirmation_request`, `clarification`, `error`) already map onto confirm-before-act behaviour.
