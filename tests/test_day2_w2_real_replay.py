"""Replay saved public W-2 responses from the failed Day 2 measurements.

The complete keyed/open pair came from run 20261115T110450049536Z. The
length-limited open reply came from run 20261115T110735883827Z. No API call is
made by these tests.
"""

import json
from pathlib import Path

from src.core_pipeline import run_text_page


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def _truth():
    truth = json.loads((ROOT / "data/ground_truth/w2_001.json").read_text(encoding="utf-8"))
    key = {item["field"]: {name: value for name, value in item.items()
                           if name not in {"field", "page"}}
           for item in truth["fields"] if item["page"] == 1}
    return truth, key


def _run(tmp_path, *, open_name="day2_w2_open.json",
         open_finish="stop", keyed_text=None):
    truth, key = _truth()

    def saved(messages):
        is_keyed = "top-level keys" in messages[0]["content"]
        if is_keyed:
            content = (keyed_text if keyed_text is not None else
                       (FIXTURES / "day2_w2_keyed.json").read_text(encoding="utf-8"))
        else:
            content = (FIXTURES / open_name).read_text(encoding="utf-8")
        return {"content": content, "finish_reason": "stop" if is_keyed else open_finish,
                "usage": {}, "api_created_at": None, "latency_seconds": 0.0}

    run = run_text_page("w2_001", ROOT / "data/pdfs/w2_001.pdf", 1,
                        truth["source_url"], answer_key=key,
                        model_request=saved, output_root=tmp_path)
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    return result, run


def _field(result, name):
    return next(item for item in result["scored"]["fields"] if item["field"] == name)


def test_real_w2_reply_marks_control_number_year_inferred(tmp_path):
    result, _ = _run(tmp_path)
    year = next(item for item in result["records"]
                if item["source_call"] == "keyed" and item["relation"] == "tax_year")
    field = _field(result, "tax_year")
    assert year["value"] == "2026"
    assert year["evidence"]["quote"] == "QA-W2-2026-01"
    assert year["origin"] == "inferred"
    assert year["state"] != "verified"
    assert field["value_match"] == "pass"
    assert field["exact"] == "fail"
    assert field["answer_status"] == "inferred"


def test_real_open_reply_repeating_keyed_names_is_counted_without_keyed_failure(tmp_path):
    result, _ = _run(tmp_path)
    assert result["call_status"]["keyed"]["complete"] is True
    assert result["call_status"]["open"]["complete"] is True
    assert result["failures"] == []
    overlaps = {item["field"]: item for item in result["open_overlaps"]}
    assert {"employer_name", "social_security_wages"} <= overlaps.keys()
    assert _field(result, "social_security_wages")["exact"] == "pass"
    assert _field(result, "social_security_wages")["answer_status"] == "answered"
    assert all(item["exact"] == "unscored" for item in result["records"]
               if item["source_call"] == "open" and item["overlaps_keyed_field"])


def test_real_open_length_limit_preserves_valid_keyed_reply(tmp_path):
    complete, _ = _run(tmp_path / "complete")
    limited, run = _run(tmp_path / "limited",
                        open_name="day2_w2_open_length.raw.json", open_finish="length")
    assert limited["complete"] is False and limited["exit_code"] == 1
    assert limited["call_status"]["keyed"]["complete"] is True
    assert limited["call_status"]["open"]["complete"] is False
    assert limited["scored"]["fields"] == complete["scored"]["fields"]
    assert len(limited["failures"]) == 1
    assert limited["failures"][0]["call"] == "open"
    assert "output limit" in limited["failures"][0]["reason"]
    assert (run / "open.raw.json").read_text(encoding="utf-8").strip() == (
        FIXTURES / "day2_w2_open_length.raw.json").read_text(encoding="utf-8").strip()


def test_real_matching_withheld_tax_without_printed_label_keeps_evidence_uncertain(tmp_path):
    result, _ = _run(tmp_path)
    field = _field(result, "federal_income_tax_withheld")
    record = next(item for item in result["records"]
                  if item["source_call"] == "keyed"
                  and item["relation"] == "federal_income_tax_withheld")
    assert field["value_match"] == "pass"
    assert field["exact"] == "pass"
    assert field["evidence_state"] == "uncertain"
    assert record["state"] == "uncertain"
    assert record["evidence"]["quote"] == "80,000.00                       9,200.00"
    assert record["evidence_support"] == "role_not_printed"


def test_duplicate_in_real_keyed_reply_is_an_extraction_failure(tmp_path):
    # Deliberately duplicate one top-level field in the saved keyed response.
    original = (FIXTURES / "day2_w2_keyed.json").read_text(encoding="utf-8")
    duplicate = original.rstrip()[:-1] + ', "social_security_wages": ' + json.dumps(
        json.loads(original)["social_security_wages"]) + '}'
    result, _ = _run(tmp_path, keyed_text=duplicate)
    field = _field(result, "social_security_wages")
    assert result["complete"] is False and result["exit_code"] == 1
    assert result["call_status"]["keyed"]["complete"] is False
    assert field["exact"] == "fail"
    assert field["answer_status"] == "extraction_failure"
    assert field["root_cause"] == {"field": "social_security_wages",
                                   "stage": "extraction", "reason": "duplicate"}
    assert {item["field"] for item in result["failures"]} == {"social_security_wages"}
