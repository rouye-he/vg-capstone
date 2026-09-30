"""Raw-event mode: imsg JSON -> ingress -> envelope."""

from pathlib import Path

from imsg_sim.ingress import Ingress
from imsg_sim.raw_events import from_imsg, iter_imsg_records, process_records
from imsg_sim.runner import ROOT, _ENVELOPE_SCHEMA, _REPLY_SCHEMA

SAMPLE = ROOT / "fixtures/imsg_watch_sample.ndjson"


def _run(cwd_root: Path = ROOT):
    import os
    old = os.getcwd()
    os.chdir(cwd_root)  # sample uses a relative fixture path
    try:
        return list(process_records(iter_imsg_records(SAMPLE.read_text().splitlines())))
    finally:
        os.chdir(old)


def test_reads_watch_lines_and_rpc_notifications():
    records = list(iter_imsg_records(SAMPLE.read_text().splitlines()))
    assert len(records) == 5
    assert records[3]["chat_id"] == 900  # unwrapped from the JSON-RPC notification


def test_sample_stream_end_to_end():
    outcomes = _run()
    statuses = [(r.status, r.reason) for _, r, _ in outcomes]
    assert statuses == [
        ("accepted", None),                 # invoice PDF
        ("dropped", "echo_from_assistant"),  # our own reply
        ("accepted", None),                 # HEIC not yet downloaded
        ("accepted", None),                 # group chat
        ("dropped", "duplicate"),           # same guid replayed
    ]
    for _, result, reply in outcomes:
        if result.envelope:
            assert list(_ENVELOPE_SCHEMA.iter_errors(result.envelope)) == []
            assert list(_REPLY_SCHEMA.iter_errors(reply)) == []


def test_pdf_attachment_is_hashed_by_reference():
    _, result, _ = _run()[0]
    att = result.envelope["attachments"][0]
    assert att["media_type"] == "application/pdf"
    assert att["validation"] == "accepted"
    assert att["size_bytes"] == 327
    assert len(att["sha256"]) == 64
    assert "SYNTHETIC INVOICE" not in str(result.envelope)


def test_missing_attachment_is_rejected_as_unavailable():
    _, result, reply = _run()[2]
    att = result.envelope["attachments"][0]
    assert att["validation"] == "rejected"
    assert att["reject_reason"] == "unavailable"
    assert att["content_ref"] is None
    assert att["processing_hint"] is None
    assert reply["kind"] == "error"


def test_group_notification_maps_to_group_envelope():
    _, result, reply = _run()[3]
    env = result.envelope
    assert env["conversation"]["type"] == "group"
    assert env["flags"]["is_group"] is True
    assert env["sender"]["handle"] == "+14125550124"
    assert env["sender"]["actor_role"] == "unresolved"
    assert reply["kind"] == "clarification"


def test_from_imsg_falls_back_to_rowid_when_guid_missing():
    raw = from_imsg({"id": 7, "chat_id": 1, "sender": "+14125550000", "text": "x", "created_at": 1790863331})  # 2026-10-01T14:02:11Z
    assert raw["guid"] == "rowid:7"
    assert raw["sent_at"].year == 2026


def test_channel_message_id_is_the_apple_guid():
    ingress = Ingress(principal_id="exec_001")
    raw = from_imsg({"guid": "APPLE-GUID-1", "chat_id": 5, "sender": "+14125550000", "text": "hi",
                     "created_at": "2026-10-01T10:00:00Z"})
    env = ingress.process(raw).envelope
    assert env["channel_message_id"] == "APPLE-GUID-1"
    assert env["sent_at"] == "2026-10-01T10:00:00Z"
