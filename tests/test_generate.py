import csv
import json
from types import SimpleNamespace

import pytest

from ai_outbound_engine.generate import ClaudeGenerator, TemplateGenerator
from ai_outbound_engine.leads import OUTPUT_COLUMNS, load_leads, write_rows
from ai_outbound_engine.pipeline import run_pipeline
from ai_outbound_engine.scoring import score_lead

EM = "\u2014"
STEPS = ("subject", "first_line", "email_1", "email_2", "email_3")


def test_template_is_deterministic_and_clean(vp_sales, config):
    score = score_lead(vp_sales, config.icp)
    a = TemplateGenerator().generate(vp_sales, config, score, "")
    b = TemplateGenerator().generate(vp_sales, config, score, "")
    assert a == b
    assert a.first_line == "Noticed Brightloop Analytics is hiring three SDRs in Austin."
    assert a.email_1.startswith("Hi Ada,\n\n" + a.first_line)
    for step in STEPS:
        assert EM not in getattr(a, step)
    for body in (a.email_1, a.email_2, a.email_3):
        assert len(body.split()) <= config.max_words


def test_template_uses_homepage_when_no_notes(leads_path, config):
    lead = next(lead for lead in load_leads(leads_path) if lead.first_name == "Tom")
    seq = TemplateGenerator().generate(lead, config, score_lead(lead, config.icp), "Carts that convert. More text.")
    assert seq.first_line == 'Was on cloudcart.example and "Carts that convert" caught my eye.'


def test_dry_run_pipeline_end_to_end(tmp_path, leads_path, config):
    rows = run_pipeline(load_leads(leads_path), config, TemplateGenerator())
    out = tmp_path / "out.csv"
    write_rows(rows, out)
    with open(out, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == OUTPUT_COLUMNS
        written = list(reader)
    scores = [int(r["icp_score"]) for r in written]
    assert scores == sorted(scores, reverse=True)
    statuses = {r["first_name"]: r["status"] for r in written}
    assert statuses["Ada"] == "ready"
    assert statuses["Marco"] == statuses["Grace"] == "skipped_low_fit"
    assert all(r["email_1"] for r in written if r["status"] == "ready")
    assert not any(r["email_1"] for r in written if r["status"] != "ready")


class FakeClient:
    """Stands in for anthropic.Anthropic so the Claude path is tested without network."""

    def __init__(self, payload, stop_reason="end_turn"):
        self.calls = []
        text = json.dumps(payload) if isinstance(payload, dict) else payload
        self._response = SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)])
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


def test_claude_generator_sanitizes_model_output(vp_sales, config):
    payload = {
        "subject": "SDR ramp at Brightloop",
        "first_line": f"Saw Brightloop is hiring three SDRs {EM} big quarter ahead.",
        "email_1": f"Hi Ada,\n\n**Saw Brightloop is hiring.** {EM} We help.\n\nMax",
        "email_2": "Hi Ada, " + "word " * 200,
        "email_3": "Hi Ada, closing the loop.\n\nMax",
    }
    client = FakeClient(payload)
    seq = ClaudeGenerator(model="test-model", client=client).generate(
        vp_sales, config, score_lead(vp_sales, config.icp), "Brightloop homepage text")
    assert seq.generator == "test-model"
    assert seq.first_line == "Saw Brightloop is hiring three SDRs, big quarter ahead."
    assert "**" not in seq.email_1 and EM not in seq.email_1
    assert len(seq.email_2.split()) <= config.max_words

    call = client.calls[0]
    assert call["model"] == "test-model"
    assert "Never use em dashes" in call["system"]
    assert "Brightloop homepage text" in call["messages"][0]["content"]
    assert call["output_config"]["format"]["type"] == "json_schema"


@pytest.mark.parametrize("payload, stop_reason", [
    ("", "refusal"),
    ("not json", "end_turn"),
    ({"subject": "missing the other fields"}, "end_turn"),
])
def test_claude_generator_falls_back_on_unusable_response(vp_sales, config, payload, stop_reason):
    client = FakeClient(payload, stop_reason=stop_reason)
    seq = ClaudeGenerator(client=client).generate(vp_sales, config, score_lead(vp_sales, config.icp), "")
    assert seq.generator == "template_fallback"
    assert seq.email_1.startswith("Hi Ada,")
