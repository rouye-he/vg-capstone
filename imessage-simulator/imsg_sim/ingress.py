"""Channel ingress: turns iMessage-shaped raw events into MessageEnvelope v0.1.

This is the logic the real iMessage adapter will run on `imsg` output. The
Simulator feeds it synthetic events so it can be tested without a Mac.

Rules implemented (see the design doc, Section 5):
  - dedupe on (channel, channel_message_id) within a 24-hour window
  - drop the assistant's own messages (echo-loop protection)
  - validate attachments by type and size; attachments travel by reference
  - never decide roles: actor_role is always "unresolved"
"""

from __future__ import annotations

import hashlib
import mimetypes
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ENVELOPE_VERSION = "0.1"
CHANNEL = "imessage"

# Proposed v0.1 values; keep in sync with the design doc's validation table.
ALLOWED_MEDIA_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/heic",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "text/plain",
}
MAX_ATTACHMENT_BYTES = 16 * 1024 * 1024  # matches OpenClaw's outbound media default
DEDUPE_WINDOW = timedelta(hours=24)

mimetypes.add_type("image/heic", ".heic")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class IngressResult:
    status: str  # "accepted" | "dropped"
    reason: str | None = None
    envelope: dict[str, Any] | None = None


@dataclass
class Ingress:
    principal_id: str
    assistant_handles: set[str] = field(default_factory=set)
    _seen: dict[tuple[str, str], datetime] = field(default_factory=dict)

    def process(self, raw: dict[str, Any], now: datetime | None = None) -> IngressResult:
        now = now or datetime.now(timezone.utc)
        guid = raw["guid"]

        # Echo loop: the assistant's own sends come back through chat.db too.
        if raw.get("is_from_me") or raw["sender"] in self.assistant_handles:
            return IngressResult("dropped", "echo_from_assistant")

        # Dedupe: the same platform message delivered twice yields one envelope.
        self._evict(now)
        key = (CHANNEL, guid)
        if key in self._seen:
            return IngressResult("dropped", "duplicate")
        self._seen[key] = now

        chat_id = raw["chat_id"]
        is_group = bool(raw.get("is_group", False))
        sender = raw["sender"]
        msg_id = _new_id("msg")

        envelope = {
            "envelope_version": ENVELOPE_VERSION,
            "message_id": msg_id,
            "correlation_id": "corr_" + msg_id.split("_", 1)[1],
            "channel": CHANNEL,
            "channel_message_id": guid,
            "conversation": {
                "conversation_id": f"imessage:chat_id:{chat_id}",
                "type": "group" if is_group else "direct",
                "reply_target": f"chat_id:{chat_id}",
            },
            "sender": {
                "handle": sender,
                "handle_type": "email" if "@" in sender else "phone",
                "actor_id": None,
                "actor_role": "unresolved",
            },
            "principal_id": self.principal_id,
            "text": raw.get("text", ""),
            "attachments": [self._attachment(a) for a in raw.get("attachments", [])],
            "in_reply_to": raw.get("reply_to_guid"),
            "flags": {"is_from_assistant": False, "is_group": is_group},
            "sent_at": _iso(raw.get("sent_at", now)),
            "received_at": _iso(now),
        }
        return IngressResult("accepted", None, envelope)

    def _evict(self, now: datetime) -> None:
        for key, seen_at in list(self._seen.items()):
            if now - seen_at > DEDUPE_WINDOW:
                del self._seen[key]

    @staticmethod
    def _attachment(att: dict[str, Any]) -> dict[str, Any]:
        """Describe an attachment by reference. Bytes never enter the envelope."""
        if "path" in att:
            path = Path(att["path"])
            data = path.read_bytes()
            filename = path.name
            size = len(data)
            digest = hashlib.sha256(data).hexdigest()
        else:  # synthetic: declared size, deterministic content, nothing on disk
            filename = att["filename"]
            size = int(att["size_bytes"])
            digest = hashlib.sha256(f"{filename}:{size}".encode()).hexdigest()

        media_type = att.get("media_type") or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        att_id = _new_id("att")

        reject_reason = None
        if media_type not in ALLOWED_MEDIA_TYPES:
            reject_reason = "unsupported_type"
        elif size > MAX_ATTACHMENT_BYTES:
            reject_reason = "too_large"

        accepted = reject_reason is None
        return {
            "attachment_id": att_id,
            "filename": filename,
            "media_type": media_type,
            "size_bytes": size,
            "sha256": digest,
            "content_ref": f"local://attachments/{att_id}" if accepted else None,
            "validation": "accepted" if accepted else "rejected",
            "reject_reason": reject_reason,
            "redaction_status": "pending" if accepted else "skipped",
        }
