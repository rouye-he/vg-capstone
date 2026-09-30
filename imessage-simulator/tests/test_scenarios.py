from pathlib import Path

import pytest
import yaml

from imsg_sim.ingress import Ingress
from imsg_sim.runner import ROOT, check, run_scenario

SCENARIOS = sorted((ROOT / "scenarios").glob("*.yaml"))


@pytest.mark.parametrize("path", SCENARIOS, ids=lambda p: p.stem)
def test_scenario(path: Path):
    scenario = yaml.safe_load(path.read_text())
    assert check(scenario, run_scenario(scenario)) == []


def test_checker_reports_wrong_expectation():
    scenario = yaml.safe_load((ROOT / "scenarios/TC-01-plain-text.yaml").read_text())
    scenario["expect"] = {"reply.kind": "error", "envelope_count": 2}
    problems = check(scenario, run_scenario(scenario))
    assert len(problems) == 2


def test_assistant_echo_is_dropped():
    ingress = Ingress(principal_id="exec_001", assistant_handles={"vgcapstonebot@gmail.com"})
    raw = {"guid": "g1", "chat_id": 42, "sender": "+14125550123", "is_from_me": True, "text": "hi"}
    assert ingress.process(raw).reason == "echo_from_assistant"


def test_envelope_never_contains_file_bytes():
    scenario = yaml.safe_load((ROOT / "scenarios/TC-02-invoice-pdf.yaml").read_text())
    env = run_scenario(scenario)["envelopes"][0]
    assert "SYNTHETIC INVOICE" not in str(env)


def test_heic_gets_conversion_hint_but_pdf_does_not():
    heic = yaml.safe_load((ROOT / "scenarios/TC-10-heic-photo.yaml").read_text())
    pdf = yaml.safe_load((ROOT / "scenarios/TC-02-invoice-pdf.yaml").read_text())
    assert run_scenario(heic)["envelopes"][0]["attachments"][0]["processing_hint"] == "convert_to_jpeg"
    assert run_scenario(pdf)["envelopes"][0]["attachments"][0]["processing_hint"] is None


def test_dedupe_window_expires_after_24h():
    from datetime import datetime, timedelta, timezone
    ingress = Ingress(principal_id="exec_001")
    t0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
    raw = {"guid": "g-late", "chat_id": 1, "sender": "+14125550123", "text": "hi"}
    assert ingress.process(raw, now=t0).status == "accepted"
    assert ingress.process(raw, now=t0 + timedelta(hours=1)).reason == "duplicate"
    assert ingress.process(raw, now=t0 + timedelta(hours=25)).status == "accepted"
