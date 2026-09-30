"""Mock assistant: stands in for the VG core agent during Simulator runs.

It does no reasoning. It only returns a ReplyEnvelope with the right `kind`,
so the channel contract (routing, rejection replies, group handling) can be
tested before the real agent or MCP tools are connected.
"""

from __future__ import annotations

from typing import Any

REASON_TEXT = {
    "unsupported_type": "this file type isn't supported",
    "too_large": "the file is larger than 16 MB",
}


def respond(envelope: dict[str, Any]) -> dict[str, Any]:
    base = {
        "correlation_id": envelope["correlation_id"],
        "in_reply_to": envelope["message_id"],
        "channel": envelope["channel"],
        "reply_target": envelope["conversation"]["reply_target"],
        "attachments": [],
    }

    if envelope["flags"]["is_group"]:
        return {**base, "kind": "clarification",
                "text": "I only handle requests in a direct message for now. Please message me directly."}

    rejected = [a for a in envelope["attachments"] if a["validation"] == "rejected"]
    if rejected:
        details = "; ".join(f"{a['filename']}: {REASON_TEXT[a['reject_reason']]}" for a in rejected)
        return {**base, "kind": "error", "text": f"I couldn't use your attachment ({details})."}

    n = len(envelope["attachments"])
    suffix = f" with {n} attachment{'s' if n != 1 else ''}" if n else ""
    return {**base, "kind": "result", "text": f"[mock] Received your request{suffix}."}
