"""Typed comparisons preserve identifiers and abstentions."""

from src.policy import score_records, typed_equal


def _record(relation, value):
    return {
        "fact_id": f"f_{relation}", "kind": "field", "subject": None,
        "relation": relation, "value": value, "origin": "extracted",
        "evidence": {"page": 1, "quote": str(value or ""), "bbox": None},
        "state": "uncertain", "reason": "Not checked.", "stage": "none",
        "exact": "unscored", "judge": "unscored", "human_verdict": None,
    }


def test_money_and_written_date_normalize_without_guessing():
    key = {
        "total_amount": {"value": 17348.36, "type": "money", "printed_marker": "₹"},
        "invoice_date": {"value": "2026-09-18", "type": "date"},
    }
    result = score_records([_record("total_amount", "₹17,348.36"),
                            _record("invoice_date", "18 September 2026")], key)
    assert result["exact_passed"] == 2
    assert result["scored"] == 2


def test_identifier_keeps_leading_zeros_and_optional_hash_prefix():
    key = {"invoice_number": {"value": "0006664805", "type": "identifier",
                              "prefix_matters": False}}
    assert score_records([_record("invoice_number", "#0006664805")], key)["exact_passed"] == 1
    assert score_records([_record("invoice_number", "6664805")], key)["exact_passed"] == 0
    key["invoice_number"]["prefix_matters"] = True
    assert score_records([_record("invoice_number", "#0006664805")], key)["exact_passed"] == 0


def test_explicit_null_passes_but_omitted_field_fails():
    key = {"payment_method": {"value": None, "type": "free_text"}}
    assert score_records([_record("payment_method", None)], key)["exact_passed"] == 1
    omitted = score_records([], key)
    assert omitted["scored"] == 1
    assert omitted["exact_passed"] == 0
    assert omitted["missing_fields"] == ["payment_method"]


def test_ambiguous_numeric_date_needs_declared_order():
    assert typed_equal("01/08/2026", "2026-08-01", "date", date_order="DMY")
    assert not typed_equal("01/08/2026", "2026-08-01", "date", date_order="MDY")
    assert not typed_equal("01/08/2026", "2026-08-01", "date")


def test_count_is_numeric_but_not_money():
    assert typed_equal("41,280", 41280, "number")


def test_weekday_and_ordinal_date_formats_normalize():
    assert typed_equal("2026-10-13", "Tuesday 13 October 2026", "date")
    assert typed_equal("2026-09-25", "25th day of September 2026", "date")


def test_wilson_range_has_an_explicit_denominator():
    from src.policy import wilson_interval

    low, high = wilson_interval(95, 97)
    assert 90 < low < 98
    assert 98 < high < 100
    assert wilson_interval(0, 0) is None


def test_report_prints_count_and_range_with_accuracy():
    from src.policy import render_policy_report

    report = render_policy_report(
        counts={"facts_in": 1, "verified": 1, "uncertain": 0, "failed": 0, "skipped": 0},
        document_types={"invoice": 1}, failures=[],
        scored={"exact_passed": 95, "scored": 97, "accuracy": 97.94},
    )
    assert "95 of 97" in report
    assert "Wilson" in report
