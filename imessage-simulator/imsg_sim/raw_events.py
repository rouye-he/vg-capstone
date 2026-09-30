"""Raw-event mode: feed real `imsg` JSON output through the ingress.

`imsg` (https://imsg.sh, used by OpenClaw's official iMessage channel) emits one
message object per line for `imsg watch --json` and `imsg history --json`, and a
JSON-RPC notification `{"method": "message", "params": {"message": {...}}}` for
`imsg rpc`. Field names below were confirmed against @openclaw/imessage 2026.9
(parseIMessageNotification) and imsg 0.15.9.

    message: id, guid, chat_id, chat_guid, chat_identifier, chat_name, sender,
             sender_name, is_from_me, is_group, text, attachments[], created_at,
             reply_to_guid, thread_originator_guid, participants[]
    attachment: original_path, mime_type, transfer_name, uti, missing

Usage:
    imsg watch --json --attachments | python -m imsg_sim.raw_events -
    python -m imsg_sim.raw_events fixtures/imsg_watch_sample.ndjson -v
    python -m imsg_sim.raw_events --live            # spawns `imsg watch` itself

Only IDs, sizes, hashes and validation status are printed by default; message
text and file contents are never logged unless -v is passed (design doc, Logging rule).
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from imsg_sim.ingress import Ingress, IngressResult
from imsg_sim.mock_assistant import respond

PRINCIPAL_ID = "exec_001"
DEFAULT_ASSISTANT_HANDLES = {"vgcapstonebot@gmail.com"}


def iter_imsg_records(lines: Iterable[str]) -> Iterator[dict[str, Any]]:
    """Yield imsg message objects from NDJSON lines (watch/history) or RPC notifications."""
    for line in lines:
        line = line.strip()
        if not line or not line.startswith("{"):
            continue  # skip log noise on the same stream
        obj = json.loads(line)
        if "jsonrpc" in obj:  # imsg rpc: {"method":"message","params":{"message":{...}}}
            if obj.get("method") != "message":
                continue
            obj = obj["params"]["message"]
        elif "messages" in obj and isinstance(obj["messages"], list):  # history as one object
            yield from obj["messages"]
            continue
        yield obj


def from_imsg(record: dict[str, Any]) -> dict[str, Any]:
    """Map one imsg message object to the ingress raw-event shape."""
    if "guid" not in record and "id" not in record:
        raise ValueError("imsg record has neither guid nor id")
    if "chat_id" not in record:
        raise ValueError("imsg record has no chat_id")
    guid = record.get("guid") or f"rowid:{record['id']}"
    return {
        "guid": guid,
        "chat_id": record["chat_id"],
        "sender": record.get("sender") or "",
        "is_from_me": bool(record.get("is_from_me", False)),
        "is_group": bool(record.get("is_group", False)),
        "text": record.get("text") or "",
        "attachments": [_attachment(a) for a in record.get("attachments") or []],
        "reply_to_guid": record.get("reply_to_guid") or record.get("thread_originator_guid"),
        "sent_at": _parse_time(record.get("created_at")),
        # kept for debugging / future routing; ingress ignores unknown keys
        "chat_guid": record.get("chat_guid"),
        "chat_identifier": record.get("chat_identifier"),
    }


def _attachment(att: dict[str, Any]) -> dict[str, Any]:
    path = (att.get("original_path") or att.get("path") or "").strip()
    filename = att.get("transfer_name") or (Path(path).name if path else "attachment")
    media_type = att.get("mime_type") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    out: dict[str, Any] = {"filename": filename, "media_type": media_type}
    if att.get("missing") or not path:
        out.update({"missing": True, "size_bytes": 0})
    else:
        out["path"] = os.path.expanduser(path)
        if not os.path.isfile(out["path"]):
            out.update({"missing": True, "size_bytes": 0})
    return out


def _parse_time(value: Any) -> datetime:
    if isinstance(value, (int, float)):  # epoch seconds
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def process_records(records: Iterable[dict[str, Any]], ingress: Ingress | None = None
                    ) -> Iterator[tuple[dict[str, Any], IngressResult, dict[str, Any] | None]]:
    ingress = ingress or Ingress(principal_id=PRINCIPAL_ID, assistant_handles=set(DEFAULT_ASSISTANT_HANDLES))
    for rec in records:
        raw = from_imsg(rec)
        result = ingress.process(raw)
        reply = respond(result.envelope) if result.envelope else None
        yield raw, result, reply


def _summary(raw: dict[str, Any], result: IngressResult, reply: dict[str, Any] | None) -> str:
    if result.status == "dropped":
        return f"DROP  guid={raw['guid']} chat={raw['chat_id']} reason={result.reason}"
    env = result.envelope
    atts = ",".join(f"{a['media_type']}:{a['validation']}" for a in env["attachments"]) or "-"
    return (f"OK    {env['message_id']} chat={raw['chat_id']} type={env['conversation']['type']} "
            f"text_len={len(env['text'])} attachments={atts} reply={reply['kind'] if reply else '-'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Feed imsg JSON output through the channel ingress")
    parser.add_argument("source", nargs="?", default="-", help="NDJSON file, or - for stdin")
    parser.add_argument("--live", action="store_true", help="spawn `imsg watch --json --attachments`")
    parser.add_argument("--chat-id", type=int, help="with --live: only this chat rowid")
    parser.add_argument("--assistant-handle", action="append", default=[],
                        help="handle(s) used by the assistant's own Apple ID (echo protection)")
    parser.add_argument("-v", "--verbose", action="store_true", help="print full envelopes (includes text)")
    args = parser.parse_args(argv)

    handles = set(args.assistant_handle) or set(DEFAULT_ASSISTANT_HANDLES)
    ingress = Ingress(principal_id=PRINCIPAL_ID, assistant_handles=handles)

    if args.live:
        cmd = ["imsg", "watch", "--json", "--attachments"]
        if args.chat_id:
            cmd += ["--chat-id", str(args.chat_id)]
        print(f"# {' '.join(cmd)}", file=sys.stderr)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, bufsize=1)
        lines: Iterable[str] = proc.stdout  # type: ignore[assignment]
    elif args.source == "-":
        lines = sys.stdin
    else:
        lines = Path(args.source).read_text().splitlines()

    try:
        for raw, result, reply in process_records(iter_imsg_records(lines), ingress):
            print(_summary(raw, result, reply))
            if args.verbose and result.envelope:
                print(json.dumps({"envelope": result.envelope, "reply": reply}, indent=2))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
