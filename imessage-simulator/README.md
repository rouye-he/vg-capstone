# iMessage Simulator (envelope mode + raw-event mode)

Pushes synthetic iMessage traffic through the channel ingress and a mock assistant, so the team can build and test the iMessage workstream without a Mac or a live Apple account. All data is synthetic: 555 phone numbers and a made-up invoice.

Design reference: *iMessage Integration: Feasibility, MessageEnvelope & Simulator*, Sections 5 and 6.

## Run it

```bash
pip install pyyaml jsonschema pytest
python -m imsg_sim.runner            # all scenarios (expect 10/10)
python -m imsg_sim.runner scenarios/TC-02-invoice-pdf.yaml -v   # one scenario, print envelopes
python -m pytest -q                  # scenarios + unit tests (expect 22 passed)

# raw-event mode: real imsg JSON through the same ingress
python -m imsg_sim.raw_events fixtures/imsg_watch_sample.ndjson      # recorded sample
imsg history --chat-id 42 --limit 20 --attachments --json | python -m imsg_sim.raw_events -
python -m imsg_sim.raw_events --live --chat-id 42                    # tails `imsg watch`
```

Raw-event mode needs a Mac with `imsg` installed and Full Disk Access granted to the terminal. It accepts `imsg watch --json`, `imsg history --json` and `imsg rpc` notifications. By default it prints only IDs, sizes and validation status, never message text; pass `-v` to see envelopes.

## Layout

| Path | What it is |
| --- | --- |
| `schemas/message_envelope.schema.json` | MessageEnvelope v0.1 (JSON Schema 2020-12) |
| `schemas/reply_envelope.schema.json` | ReplyEnvelope v0.1 |
| `imsg_sim/ingress.py` | Raw iMessage event → envelope: dedupe, echo drop, attachment checks |
| `imsg_sim/mock_assistant.py` | Stand-in for the VG agent; returns a reply of the right `kind` |
| `imsg_sim/runner.py` | Loads scenarios, runs them, validates schemas, checks `expect` |
| `imsg_sim/raw_events.py` | Raw-event mode: maps real `imsg` JSON (watch / history / rpc) onto the ingress |
| `scenarios/` | TC-01 to TC-10 |
| `fixtures/` | Synthetic files used by scenarios, plus `imsg_watch_sample.ndjson` (imsg output shape, fake data) |

## Writing a scenario

```yaml
id: TC-02-invoice-pdf
title: Text + PDF invoice
sender: "+14125550123"      # optional, default shown
chat_id: 42                 # optional, default shown
messages:
  - text: "Can you check this invoice?"
    attachments: [fixtures/invoice_acme_0923.pdf]
    # guid, sender, is_from_me, is_group, reply_to_guid, sent_at are optional per message
    # sent_at: ISO timestamp, or "+N" seconds after the scenario start (2026-10-01T14:00:00Z)
expect:
  envelope_count: 1
  attachments[0].validation: accepted
  reply.kind: result
  reply.text: "~substring match"   # a leading ~ means "contains"
```

Shorthands in `expect`: `envelope.` = first envelope, `attachments[i]` = its attachments, `reply.` = first reply. Also available: `envelope_count`, `dropped_count`, `dropped[i].reason`, `envelopes[i]`, `replies[i]`.

Attachments can be a fixture path, or declared without a real file (useful for oversized cases):

```yaml
attachments:
  - {filename: scan_q3.pdf, media_type: application/pdf, size_bytes: 17825792}
```

## Current rules (v0.1, proposed)

- Dedupe on `channel` + `channel_message_id` (the Apple GUID) within 24 hours
- Drop messages from the assistant's own handle or flagged `is_from_me` (echo loop)
- Allowed types: PDF, PNG, JPEG, HEIC, DOCX, XLSX, CSV, TXT; max 16 MB
- Attachments imsg reports as `missing` (not downloaded yet) are rejected with `reject_reason: unavailable`
- HEIC is accepted and flagged `processing_hint: convert_to_jpeg` for downstream tools
- `actor_role` is always `unresolved`; VG's IAM (or OpenClaw pairing) assigns roles
- Group chats produce an envelope with `is_group: true`; the mock replies asking for a DM
- Split-send (command, then URL): imsg 0.13.1+ coalesces the rows upstream, the ingress never merges on its own
- Attachments travel by reference; envelopes never contain file bytes

## Schema changes since the design doc

Both are additive; envelopes produced before still validate.

- `attachments[].reject_reason` gained the value `unavailable`
- `attachments[].processing_hint` (optional): `null` or `convert_to_jpeg`

## Test cases

| ID | Scenario | Checks |
| --- | --- | --- |
| TC-01 | Plain text | one envelope, reply to the same `chat_id` |
| TC-02 | Text + PDF | accepted, sha256 set, redaction pending |
| TC-03 | `.zip` | rejected `unsupported_type`, error reply |
| TC-04 | 17 MB PDF | rejected `too_large`, error reply |
| TC-05 | Same GUID twice | one envelope, one `duplicate` drop |
| TC-06 | Echo loop | `is_from_me` and own-handle rows both dropped |
| TC-07 | Unknown sender | envelope built, `actor_role: unresolved`, `actor_id: null` |
| TC-08 | Group chat | `type: group`, clarification reply |
| TC-09 | Split-send | coalesced row is one envelope, later message is a second one, `sent_at` preserved |
| TC-10 | HEIC photo | accepted, `processing_hint: convert_to_jpeg` |

## Next

- Fake `imsg rpc` stub (Simulator mode 3) so an unmodified OpenClaw Gateway can be tested on Linux CI
- Replace the mock assistant with a call into the OpenClaw Gateway once the bot Apple ID activates
