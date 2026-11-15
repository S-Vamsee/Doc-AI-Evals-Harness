"""Exact money scoring preserves the owner-confirmed printed currency marker."""

from src.policy import score_records, typed_equal


def record(value):
    return {
        "fact_id": "f-money", "kind": "field", "subject": None,
        "relation": "total_due", "value": value, "origin": "extracted",
        "evidence": {"page": 1, "quote": str(value), "bbox": None},
        "state": "uncertain", "reason": "Unchecked", "stage": "none",
        "exact": "unscored", "judge": "unscored", "human_verdict": None,
    }


def test_currency_marker_is_required_when_pdf_prints_one():
    assert typed_equal("$53.78", 53.78, "money", printed_marker="$")
    assert not typed_equal("53.78", 53.78, "money", printed_marker="$")
    assert typed_equal("₹17,348.36", 17348.36, "money",
                       printed_marker="₹")
    assert typed_equal("INR 17,348.36", 17348.36, "money",
                       printed_marker="₹ and rupees")
    assert typed_equal("17,348.36 rupees", 17348.36, "money",
                       printed_marker="₹")
    assert not typed_equal("17,348.36", 17348.36, "money",
                           printed_marker="₹")


def test_printed_code_or_no_marker_is_preserved():
    assert typed_equal("28.00 USD", 28, "money", printed_marker="USD")
    assert typed_equal("325.41 CAD", 325.41, "money", printed_marker="CAD")
    assert not typed_equal("28.00", 28, "money", printed_marker="USD")
    assert typed_equal("80000.00", 80000, "money", printed_marker="none")
    assert not typed_equal("$80000.00", 80000, "money",
                           printed_marker="none")


def test_dollar_sign_and_usd_code_are_not_interchangeable():
    assert not typed_equal("USD 329.40", 329.4, "money", printed_marker="$")
    assert not typed_equal("$28.00", 28, "money", printed_marker="USD")


def test_column_marker_allows_bare_figure_but_not_invented_code():
    assert typed_equal("30333", 30333, "money", printed_marker="$",
                       marker_scope="column")
    assert not typed_equal("USD 30333", 30333, "money", printed_marker="$",
                           marker_scope="column")


def test_score_records_passes_key_currency_metadata_to_exact_comparison():
    key = {"total_due": {"value": 53.78, "type": "money",
                         "printed_marker": "$", "proposed_currency": None,
                         "currency_basis": "printed"}}
    assert score_records([record("$53.78")], key)["exact_passed"] == 1
    assert score_records([record("53.78")], key)["exact_passed"] == 0


def test_existing_runner_uses_printed_marker_in_money_score():
    from src.score import score_document
    truth = {"doc_id": "utility_001", "fields": [{"field": "total_due",
        "value": 53.78, "type": "money", "printed_marker": "$",
        "proposed_currency": None, "currency_basis": "printed",
        "marker_scope": "adjacent", "unit_scale": 1}]}
    extracted = {"model": "deepseek-flash", "fields": [{"field": "total_due",
        "value": "53.78", "source_page": 1}], "usage": {
        "prompt_tokens": 0, "completion_tokens": 0}, "api_created_at": 0,
        "latency_seconds": 0.0}
    result = score_document(extracted, truth, ["Total due $53.78"])
    assert result["correct"] == 0
