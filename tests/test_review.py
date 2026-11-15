"""Machine-first review queue: bounded work, explicit omissions, separate verdicts."""

import pytest

from src.policy import FactRecord


def _fact(number: int, state: str, quote: str = "Invoice A-17") -> FactRecord:
    return FactRecord.model_validate({
        "fact_id": f"f{number:03d}", "kind": "field", "subject": None,
        "relation": f"field_{number}", "value": "A-17", "origin": "extracted",
        "evidence": {"page": 1, "quote": quote,
                     "bbox": [72, 60, 130, 75] if state == "verified" else None},
        "state": state, "reason": "Needs review." if state == "uncertain" else "Located by code.",
        "stage": "evidence_check", "exact": "unscored", "judge": "unscored",
        "human_verdict": None,
    })


def test_uncertain_queue_is_capped_without_promoting_overflow():
    from src.review import build_review_queue

    records = [_fact(n, "uncertain") for n in range(15)]
    queue = build_review_queue(records, "Invoice A-17", uncertain_cap=10, sample_size=3, seed=7)
    assert len(queue["uncertain"]) == 10
    assert queue["unreviewed_uncertain"] == 5
    assert all(item.state == "uncertain" for item in records)


def test_verified_sample_and_uncovered_lines_are_visible():
    from src.review import build_review_queue

    records = [_fact(n, "verified") for n in range(6)]
    page = "Invoice A-17\nDue date 2026-10-18\nUnmatched footer"
    queue = build_review_queue(records, page, uncertain_cap=10, sample_size=3, seed=7)
    assert len(queue["verified_sample"]) == 3
    assert {item["text"] for item in queue["uncovered_text"]} == {
        "Due date 2026-10-18", "Unmatched footer"}


def test_human_verdict_does_not_change_machine_state():
    from src.review import apply_human_verdicts, build_review_queue

    records = [_fact(1, "uncertain")]
    queue = build_review_queue(records, "Invoice A-17", seed=7)
    compared = apply_human_verdicts(records, queue, {"f001": "wrong"}, missing=[])
    assert compared["records"][0].state == "uncertain"
    assert compared["records"][0].human_verdict == "wrong"
    assert compared["human_reviewed"] == 1
    with pytest.raises(ValueError):
        apply_human_verdicts(records, queue, {"f001": "verified"}, missing=[])


def test_exact_failure_enters_queue_without_changing_evidence_state():
    from src.review import apply_human_verdicts, build_review_queue

    failed = _fact(1, "verified").model_copy(update={
        "relation": "invoice_number", "exact": "fail"})
    passed = _fact(2, "verified").model_copy(update={
        "relation": "vendor_name", "exact": "pass"})
    scored = {"fields": [
        {"field": "invoice_number", "exact": "fail",
         "extracted": "A-17", "expected": "A-18"},
        {"field": "vendor_name", "exact": "pass",
         "extracted": "A-17", "expected": "A-17"},
    ]}
    queue = build_review_queue([failed, passed], "Invoice A-17", scored=scored,
                               sample_size=0)
    assert len(queue["possible_near_matches"]) == 1
    item = queue["possible_near_matches"][0]
    assert item["fact_id"] == "f001"
    assert item["expected"] == "A-18"
    assert item["extracted"] == "A-17"
    assert item["evidence"]["bbox"] is not None
    assert item["evidence_state"] == "verified"
    reviewed = apply_human_verdicts([failed, passed], queue, {"f001": "right"}, [])
    assert reviewed["records"][0].exact == "fail"
    assert reviewed["records"][0].state == "verified"
    assert reviewed["records"][0].human_verdict == "right"


def test_uncertain_exact_failure_is_listed_once():
    from src.review import build_review_queue

    record = _fact(1, "uncertain").model_copy(update={
        "relation": "invoice_number", "exact": "fail"})
    scored = {"fields": [{"field": "invoice_number", "exact": "fail",
                           "extracted": "A-17", "expected": "A-18"}]}
    queue = build_review_queue([record], "Invoice A-17", scored=scored,
                               sample_size=0)
    assert len(queue["possible_near_matches"]) == 1
    assert queue["uncertain"] == []
