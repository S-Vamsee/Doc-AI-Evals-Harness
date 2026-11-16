"""Presence and type-aware support are both needed before verification."""

import pymupdf

from src.policy import FactRecord, verify_text_record


def _fact(relation, value, quote, kind="labelled_value"):
    return FactRecord.model_validate({
        "fact_id": "f001", "kind": kind, "subject": None,
        "relation": relation, "value": value, "origin": "extracted",
        "evidence": {"page": 1, "quote": quote, "bbox": None},
        "state": "uncertain", "reason": "Pending", "stage": "none",
        "exact": "unscored", "judge": "unscored", "human_verdict": None,
    })


def test_date_and_amount_are_supported_by_typed_printed_forms():
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Invoice date 18 September 2026")
    page.insert_text((72, 92), "Total amount $1,280.40")
    date = verify_text_record(_fact("invoice_date", "2026-09-18",
                                    "Invoice date 18 September 2026", "date_or_time"),
                              page, {"type": "date"})
    money = verify_text_record(_fact("total_amount", "1280.40",
                                     "Total amount $1,280.40", "amount"),
                               page, {"type": "money", "printed_marker": "$"})
    assert date.state == money.state == "verified"
    assert date.evidence_support == money.evidence_support == "supported"
    pdf.close()


def test_number_inside_another_number_does_not_count_as_support():
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Days open 3020")
    checked = verify_text_record(_fact("days_open", "302", "Days open 3020"),
                                 page, {"type": "number"})
    assert checked.state == "uncertain"
    assert checked.evidence_support == "unsupported"
    assert "support" in checked.reason.lower()
    pdf.close()


def test_number_words_in_quote_support_digit_value():
    from src.policy import value_supported_by_quote

    quote = "The window is extended from ten to fifteen business days."
    assert value_supported_by_quote(15, quote, "number")
    assert value_supported_by_quote("fifteen", quote, "number")
    assert not value_supported_by_quote(16, quote, "number")
