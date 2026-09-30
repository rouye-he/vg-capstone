"""Scenario runner (Simulator envelope mode).

Usage:
    python -m imsg_sim.runner                 # run every scenario in scenarios/
    python -m imsg_sim.runner scenarios/TC-02-invoice-pdf.yaml -v

Each scenario sends synthetic iMessage events through the ingress, hands every
accepted envelope to the mock assistant, validates both envelopes and replies
against the JSON Schemas, then checks the scenario's `expect` block.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from imsg_sim.ingress import Ingress
from imsg_sim.mock_assistant import respond

ROOT = Path(__file__).resolve().parent.parent
PRINCIPAL_ID = "exec_001"
ASSISTANT_HANDLE = "vgcapstonebot@gmail.com"

_ENVELOPE_SCHEMA = Draft202012Validator(
    json.loads((ROOT / "schemas/message_envelope.schema.json").read_text()), format_checker=FormatChecker())
_REPLY_SCHEMA = Draft202012Validator(
    json.loads((ROOT / "schemas/reply_envelope.schema.json").read_text()), format_checker=FormatChecker())

_ALIASES = [("envelope.", "envelopes[0]."), ("reply.", "replies[0]."), ("attachments[", "envelopes[0].attachments[")]


def run_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    ingress = Ingress(principal_id=PRINCIPAL_ID, assistant_handles={ASSISTANT_HANDLE})
    sender = scenario.get("sender", "+14125550123")
    chat_id = scenario.get("chat_id", 42)

    envelopes, replies, dropped = [], [], []
    for i, msg in enumerate(scenario["messages"]):
        raw = {
            "guid": msg.get("guid", f"{scenario['id']}-guid-{i}"),
            "chat_id": msg.get("chat_id", chat_id),
            "sender": msg.get("sender", sender),
            "is_from_me": msg.get("is_from_me", False),
            "is_group": msg.get("is_group", scenario.get("is_group", False)),
            "text": msg.get("text", ""),
            "attachments": [_resolve_attachment(a) for a in msg.get("attachments", [])],
        }
        result = ingress.process(raw)
        if result.status == "dropped":
            dropped.append({"guid": raw["guid"], "reason": result.reason})
            continue
        envelopes.append(result.envelope)
        replies.append(respond(result.envelope))

    return {
        "envelope_count": len(envelopes),
        "dropped_count": len(dropped),
        "envelopes": envelopes,
        "replies": replies,
        "dropped": dropped,
    }


def check(scenario: dict[str, Any], outcome: dict[str, Any]) -> list[str]:
    failures = []
    for env in outcome["envelopes"]:
        failures += [f"envelope schema: {e.message}" for e in _ENVELOPE_SCHEMA.iter_errors(env)]
    for rep in outcome["replies"]:
        failures += [f"reply schema: {e.message}" for e in _REPLY_SCHEMA.iter_errors(rep)]

    for path, expected in scenario.get("expect", {}).items():
        try:
            actual = _get(outcome, path)
        except (KeyError, IndexError, TypeError):
            failures.append(f"{path}: missing (expected {expected!r})")
            continue
        if isinstance(expected, str) and expected.startswith("~"):
            if expected[1:].lower() not in str(actual).lower():
                failures.append(f"{path}: {actual!r} does not contain {expected[1:]!r}")
        elif actual != expected:
            failures.append(f"{path}: expected {expected!r}, got {actual!r}")
    return failures


def _resolve_attachment(att: Any) -> dict[str, Any]:
    if isinstance(att, str):
        return {"path": str(ROOT / att)}
    return att  # synthetic: {filename, size_bytes, media_type?}


def _get(obj: Any, path: str) -> Any:
    for short, full in _ALIASES:
        if path.startswith(short):
            path = full + path[len(short):]
            break
    for token in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        obj = obj[int(token[1:-1])] if token.startswith("[") else obj[token]
    return obj


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run iMessage Simulator scenarios")
    parser.add_argument("paths", nargs="*", default=[str(ROOT / "scenarios")])
    parser.add_argument("-v", "--verbose", action="store_true", help="print envelopes and replies")
    args = parser.parse_args(argv)

    files = []
    for p in map(Path, args.paths):
        files += sorted(p.glob("*.yaml")) if p.is_dir() else [p]

    failed = 0
    for f in files:
        scenario = yaml.safe_load(f.read_text())
        outcome = run_scenario(scenario)
        problems = check(scenario, outcome)
        status = "PASS" if not problems else "FAIL"
        failed += bool(problems)
        print(f"{status}  {scenario['id']:<28} {scenario.get('title', '')}")
        for msg in problems:
            print(f"        - {msg}")
        if args.verbose:
            print(json.dumps({k: outcome[k] for k in ("envelopes", "replies", "dropped")}, indent=2))

    print(f"\n{len(files) - failed}/{len(files)} scenarios passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
