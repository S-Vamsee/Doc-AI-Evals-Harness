"""Open overlaps must not hide a keyed near-match from review."""

from src.policy import FactRecord
from src.review import build_review_queue


def _record(fact_id, source_call, value):
    return FactRecord.model_validate({
        "fact_id": fact_id, "kind": "identifier", "subject": None,
        "relation": "invoice_number", "value": value, "origin": "extracted",
        "evidence": {"page": 1, "quote": "Invoice number A-17", "bbox": None},
        "state": "uncertain", "reason": "Pending", "stage": "evidence_check",
        "exact": "fail" if source_call == "keyed" else "unscored",
        "judge": "unscored", "human_verdict": None,
        "source_call": source_call,
    })


def test_keyed_near_match_stays_in_queue_with_same_named_open_fact():
    keyed = _record("f001", "keyed", "A-18")
    opened = _record("f002", "open", "A-17")
    scored = {"fields": [{"field": "invoice_number", "exact": "fail",
                           "extracted": "A-18", "expected": "A-17"}]}
    queue = build_review_queue([keyed, opened], "Invoice number A-17",
                               scored=scored)
    assert [item["fact_id"] for item in queue["possible_near_matches"]] == ["f001"]
