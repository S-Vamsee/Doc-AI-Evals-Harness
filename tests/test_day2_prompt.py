"""Day 2: ask for role-bearing, printable evidence spans."""

from src.core_pipeline import SYSTEM_PROMPT


def test_prompt_requests_full_printed_label_and_value_line():
    assert "full printed phrase or line" in SYSTEM_PROMPT
    assert "both the printed label and the value" in SYSTEM_PROMPT
    assert "short exact, contiguous excerpt" not in SYSTEM_PROMPT


def test_open_prompt_excludes_keyed_relation_names():
    assert "Do not output any of the excluded field names" in SYSTEM_PROMPT
    assert "Use the exact requested relation name once" not in SYSTEM_PROMPT
