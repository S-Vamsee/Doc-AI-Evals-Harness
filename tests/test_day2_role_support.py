"""A bare value is not machine-verified as its claimed role."""

import pymupdf

from src.policy import FactRecord, verify_text_record
from src.review import build_review_queue


def test_bare_value_has_separate_role_not_printed_outcome_and_review_sample():
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "A-17")
    record = FactRecord.model_validate({
        "fact_id": "f001", "kind": "identifier", "subject": None,
        "relation": "invoice_number", "value": "A-17", "origin": "extracted",
        "evidence": {"page": 1, "quote": "A-17", "bbox": None},
        "state": "uncertain", "reason": "Pending", "stage": "none",
        "exact": "unscored", "judge": "unscored", "human_verdict": None,
    })
    checked = verify_text_record(record, page)
    assert checked.state == "uncertain"
    assert checked.evidence_support == "role_not_printed"
    queue = build_review_queue([checked], "A-17")
    assert [item["fact_id"] for item in queue["role_not_printed_sample"]] == ["f001"]
    pdf.close()
