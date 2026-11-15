"""The exported test sheet explains concrete inputs and expected outcomes."""

from scripts.export_test_inventory import _assertions, humanize, describe_test


def test_test_name_becomes_readable_check_with_input_and_expected_result():
    row = describe_test("tests.test_day2_abstention",
                        "test_explicit_null_is_scored_as_abstention_and_not_reviewed")
    assert humanize("test_wrong_claimed_box_cannot_pass") == "Wrong claimed box cannot pass"
    assert "null" in row["plain_language_check"].lower()
    assert "invoice" in row["input"].lower()
    assert "abstention" in row["expected_result"].lower()


def test_exception_assertions_are_visible_in_exported_cases():
    cases = [
        ("test_calibration_sheet", "test_unfounded_source_excerpt_is_rejected"),
        ("test_day2_keyed_contract", "test_invalid_keyed_shape_is_an_extraction_failure"),
        ("test_development_compare", "test_compare_refuses_different_code_or_inputs"),
        ("test_environments", "test_heldback_refuses_unfrozen_set"),
        ("test_judge_calibration", "test_tiny_or_unbalanced_set_cannot_activate_judge"),
        ("test_judge_calibration", "test_missing_human_label_cannot_activate_judge"),
        ("test_rules", "test_rule_02_only_three_fact_states"),
        ("test_rules", "test_rule_06_mismatched_counts_block_report"),
    ]
    for module, name in cases:
        assertion = _assertions(module, name)
        assert "raises" in assertion
        assert "ValueError" in assertion or "RuntimeError" in assertion
