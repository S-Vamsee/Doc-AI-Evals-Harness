"""The saved-run audit distinguishes bare values from printed phrases."""

from scripts.analyze_multi_quote import classify_quote, phrase_occurrences


def test_quote_classification_does_not_call_every_search_box_a_repeat():
    assert classify_quote({"kind": "amount", "value": "42", "evidence": {"quote": "42"}}) == "bare_value"
    assert classify_quote({"kind": "amount", "value": "42", "evidence": {"quote": "Total amount 42"}}) == "label_and_value"
    assert classify_quote({"kind": "statement", "value": "All terms remain.",
                           "evidence": {"quote": "All terms remain."}}) == "statement_or_row"
    assert phrase_occurrences("Total amount 42\nOther line", "Total   amount 42") == 1
    assert phrase_occurrences("Total amount 42\nTotal amount 42", "Total amount 42") == 2
