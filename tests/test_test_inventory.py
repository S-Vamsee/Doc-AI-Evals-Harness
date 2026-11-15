"""The exported test sheet explains concrete inputs and expected outcomes."""

from scripts.export_test_inventory import humanize, describe_test


def test_test_name_becomes_readable_check_with_input_and_expected_result():
    row = describe_test("tests.test_day2_abstention",
                        "test_explicit_null_is_scored_as_abstention_and_not_reviewed")
    assert humanize("test_wrong_claimed_box_cannot_pass") == "Wrong claimed box cannot pass"
    assert "null" in row["plain_language_check"].lower()
    assert "invoice" in row["input"].lower()
    assert "abstention" in row["expected_result"].lower()
