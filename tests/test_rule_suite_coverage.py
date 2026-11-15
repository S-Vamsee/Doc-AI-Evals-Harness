"""Ensure the test suite names and exercises all twelve standing rules."""

from pathlib import Path
import re

from src.policy import require_rule_coverage


def test_all_twelve_rules_have_named_tests():
    source = (Path(__file__).parent / "test_rules.py").read_text(encoding="utf-8")
    covered = {int(number) for number in re.findall(r"^def test_rule_(\d{2})_", source, re.M)}
    assert require_rule_coverage(covered)
