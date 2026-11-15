"""Positive and negative checks for source localization on text pages."""

import pymupdf

from src.policy import FactRecord, verify_text_record


def _record(box=None):
    return FactRecord.model_validate({
        "fact_id": "f001", "kind": "field", "subject": None,
        "relation": "invoice_number", "value": "A-17", "origin": "extracted",
        "evidence": {"page": 1, "quote": "Invoice A-17", "bbox": box},
        "state": "uncertain", "reason": "Not yet checked.", "stage": "none",
        "exact": "unscored", "judge": "unscored", "human_verdict": None,
    })


def test_unique_text_quote_is_located_by_code():
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Invoice A-17")
    result = verify_text_record(_record(), page)
    assert result.state == "verified"
    assert result.evidence.bbox is not None
    assert result.evidence.bbox[0] >= 70
    pdf.close()


def test_wrong_claimed_box_cannot_pass():
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Invoice A-17")
    result = verify_text_record(_record([300, 300, 350, 320]), page)
    assert result.state == "uncertain"
    assert result.evidence.bbox is None
    pdf.close()


def test_normalized_date_and_money_still_require_a_real_quote():
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Invoice date 18 September 2026")
    page.insert_text((72, 92), "Total INR 17,348.36")
    date_data = _record().model_dump()
    date_data["relation"] = "invoice_date"
    date_data["value"] = "2026-09-18"
    date_data["evidence"]["quote"] = "Invoice date 18 September 2026"
    money_data = _record().model_dump()
    money_data["relation"] = "total_amount"
    money_data["value"] = "17348.36"
    money_data["evidence"]["quote"] = "Total INR 17,348.36"
    assert verify_text_record(FactRecord.model_validate(date_data), page).state == "verified"
    assert verify_text_record(FactRecord.model_validate(money_data), page).state == "verified"
    pdf.close()


def test_year_inside_reference_id_does_not_verify_tax_year():
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Reference QA-W2-2026-01")
    data = _record().model_dump()
    data["relation"] = "tax_year"
    data["value"] = "2026"
    data["evidence"]["quote"] = "QA-W2-2026-01"
    result = verify_text_record(FactRecord.model_validate(data), page)
    assert result.state == "uncertain"
    assert result.evidence.bbox is None
    pdf.close()
