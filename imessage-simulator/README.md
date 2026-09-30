# iMessage Simulator (envelope mode)

Pushes synthetic iMessage traffic through the channel ingress and a mock assistant, so the team can build and test the iMessage workstream without a Mac or a live Apple account. All data is synthetic: 555 phone numbers and a made-up invoice.

Design reference: *iMessage Integration: Feasibility, MessageEnvelope & Simulator*, Sections 5 and 6.

## Run it

```bash
pip install pyyaml jsonschema pytest
python -m imsg_sim.runner            # all scenarios
python -m imsg_sim.runner scenarios/TC-02-invoice-pdf.yaml -v   # one scenario, print envelopes
python -m pytest -q                  # scenarios + unit tests
```

## Layout

| Path | What it is |
| --- | --- |
| `schemas/message_envelope.schema.json` | MessageEnvelope v0.1 (JSON Schema 2020-12) |
| `schemas/reply_envelope.schema.json` | ReplyEnvelope v0.1 |
| `imsg_sim/ingress.py` | Raw iMessage event → envelope: dedupe, echo drop, attachment checks |
| `imsg_sim/mock_assistant.py` | Stand-in for the VG agent; returns a reply of the right `kind` |
| `imsg_sim/runner.py` | Loads scenarios, runs them, validates schemas, checks `expect` |
| `scenarios/` | TC-01 to TC-05 |
| `fixtures/` | Synthetic files used by scenarios |

## Writing a scenario

```yaml
id: TC-02-invoice-pdf
title: Text + PDF invoice
sender: "+14125550123"      # optional, default shown
chat_id: 42                 # optional, default shown
messages:
  - text: "Can you check this invoice?"
    attachments: [fixtures/invoice_acme_0923.pdf]
    # guid, is_from_me, is_group are optional per message
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

- Dedupe on `channel` + `channel_message_id` within 24 hours
- Drop messages from the assistant's own handle (echo loop)
- Allowed types: PDF, PNG, JPEG, HEIC, DOCX, XLSX, CSV, TXT; max 16 MB
- `actor_role` is always `unresolved`; VG's IAM assigns roles
- Attachments travel by reference; envelopes never contain file bytes

## Next

- TC-06 to TC-10 (echo loop, unknown sender, group chat, split-send, HEIC)
- Raw-event mode: feed real `imsg` JSON output through `ingress.py` once the bot's iMessage account is active
