"""The twelve standing rules, exercised with deliberately broken inputs.

These tests use no API key, network connection, or live model call.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pymupdf
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def fact(**changes):
    item = {
        "fact_id": "f001", "kind": "field", "subject": None,
        "relation": "invoice_number", "value": "A-17", "origin": "extracted",
        "evidence": {"page": 1, "quote": "Invoice A-17", "bbox": None},
        "state": "uncertain", "reason": "Evidence has not been checked.",
        "stage": "none", "exact": "unscored", "judge": "unscored",
        "human_verdict": None,
    }
    item.update(changes)
    return item


def test_rule_01_no_score_without_human_key():
    from src import policy

    result = policy.score_records([fact()], answer_key=None)
    assert result["scored"] == 0
    assert result["accuracy"] is None
    assert result["label"] == "extracted, unscored"


def test_rule_02_only_three_fact_states():
    from src import policy

    with pytest.raises(ValueError):
        policy.FactRecord.model_validate(fact(state="found"))
    with pytest.raises(ValueError):
        policy.FactRecord.model_validate(fact(state="pass"))


def test_rule_03_fabricated_quote_cannot_be_verified():
    from src import policy

    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Invoice A-17")
    checked = policy.verify_text_record(
        policy.FactRecord.model_validate(fact(evidence={"page": 1, "quote": "Invoice B-99", "bbox": None})),
        page,
    )
    assert checked.state == "uncertain"
    assert checked.evidence.bbox is None
    pdf.close()


def test_rule_04_single_vision_reading_cannot_verify_a_scan():
    from src import policy

    record = policy.FactRecord.model_validate(fact())
    checked = policy.verify_scan_record(record, vision_text="Invoice A-17", independent_words=[])
    assert checked.state == "uncertain"
    assert checked.evidence.bbox is None


def test_rule_05_simulated_timeout_is_a_recorded_failure():
    from src import policy

    def timeout():
        raise TimeoutError("OCR did not respond")

    result = policy.record_stage_call("ocr", timeout)
    assert result["complete"] is False
    assert result["exit_code"] != 0
    assert result["failures"][0]["stage"] == "ocr"
    assert "OCR did not respond" in result["failures"][0]["reason"]


def test_rule_06_mismatched_counts_block_report():
    from src import policy

    with pytest.raises(ValueError):
        policy.validate_tally({"facts_in": 3, "verified": 1, "uncertain": 1,
                               "failed": 0, "skipped": 0})


def test_rule_07_inferred_fact_and_null_are_not_guesses():
    from src import policy

    with pytest.raises(ValueError):
        policy.FactRecord.model_validate(fact(origin="inferred", state="verified"))
    null_fact = policy.FactRecord.model_validate(fact(value=None, state="uncertain"))
    assert null_fact.value is None
    assert null_fact.state == "uncertain"


def test_rule_08_judge_requires_other_model_and_wrong_examples():
    from src import policy

    pairs = [{"expected_match": True, "judge_match": True}]
    with pytest.raises(ValueError):
        policy.calibrate_judge(pairs, extractor_model="deepseek-flash", judge_model="deepseek-flash")
    with pytest.raises(ValueError):
        policy.calibrate_judge(pairs, extractor_model="deepseek-flash", judge_model="other-model")
    result = policy.score_records([fact(value="B-99")],
                                  answer_key={"invoice_number": {"value": "A-17", "type": "identifier"}},
                                  judge_results={"invoice_number": True})
    assert result["exact_passed"] == 0
    assert result["judge_passed"] == 1


def test_rule_09_document_instruction_stays_data():
    from src import policy

    hostile_page = (FIXTURES / "injection_page.txt").read_text(encoding="utf-8")
    messages = policy.build_extraction_messages(hostile_page)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert hostile_page not in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert hostile_page in messages[1]["content"]


def test_rule_10_manifest_records_hashes_and_cache_use():
    from src import policy

    manifest = policy.make_manifest(model_label="deepseek-flash", prompt="extract page facts",
                                    pdf_bytes=b"%PDF example", code_version="abc123",
                                    cache_steps={"vision": True, "extractor": False})
    assert manifest["model_label"] == "deepseek-flash"
    assert manifest["prompt_sha256"] == hashlib.sha256(b"extract page facts").hexdigest()
    assert manifest["input_sha256"] == hashlib.sha256(b"%PDF example").hexdigest()
    assert manifest["code_version"] == "abc123"
    assert manifest["cache_steps"]["vision"] is True


def test_rule_11_general_claim_rejected_for_narrow_test():
    from src import policy

    with pytest.raises(ValueError):
        policy.validate_scope_claim("works for all document types", {"invoice": 1})
    assert "1 invoice" in policy.scope_statement({"invoice": 1})


def test_rule_12_suite_must_cover_every_hard_rule():
    from src import policy

    with pytest.raises(ValueError):
        policy.require_rule_coverage(set(range(1, 12)))
    assert policy.require_rule_coverage(set(range(1, 13))) is True
