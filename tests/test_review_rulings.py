"""The owner review file is the source for deterministic and future judge rulings."""

from src.policy import score_records, typed_equal


def test_money_comparison_checks_reference_marker_by_default():
    assert typed_equal("53.78", 53.78, "money")
    assert not typed_equal("$53.78", 53.78, "money")
    assert not typed_equal("53.78", "$53.78", "money")
    assert typed_equal("INR 17,348.36", "₹17,348.36", "money")
    assert not typed_equal("USD 53.78", "$53.78", "money")


def test_score_records_defaults_to_marker_check_without_key_option():
    record = {
        "fact_id": "money", "kind": "field", "subject": None,
        "relation": "total_due", "value": "$53.78", "origin": "extracted",
        "evidence": {"page": 1, "quote": "$53.78", "bbox": None},
        "state": "uncertain", "reason": "Unchecked", "stage": "none",
        "exact": "unscored", "judge": "unscored", "human_verdict": None,
    }
    key = {"total_due": {"value": 53.78, "type": "money"}}
    assert score_records([record], key)["exact_passed"] == 0


def test_scorer_and_future_judge_prompt_load_review_file():
    from src.rulings import load_review_rulings
    from src.judge import JUDGE_SYSTEM_PROMPT

    rulings = load_review_rulings()
    assert rulings["currency_aliases"] == [["₹", "INR", "rupees", "Indian rupees"]]
    assert rulings["missing_currency_marker_is_different"] is True
    assert rulings["column_bare_value_allowed"] is True
    assert " ".join(rulings["judge_prompt_lines"]) == JUDGE_SYSTEM_PROMPT


def test_money_alias_decision_comes_from_loaded_rulings(monkeypatch):
    from src import policy

    real = policy.load_review_rulings()
    alternate = dict(real, currency_aliases=[["$", "USD"]])
    monkeypatch.setattr(policy, "load_review_rulings", lambda: alternate)
    assert policy.typed_equal("USD 53.78", "$53.78", "money")
