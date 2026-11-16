"""Load the owner's comparison rulings from the review document."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
import re


REVIEW_PATH = Path(__file__).resolve().parents[1] / "data" / "calibration" / "REVIEW.md"
_BLOCK = re.compile(
    r"<!-- EVAL_RULINGS_START -->\s*```json\s*(.*?)\s*```\s*<!-- EVAL_RULINGS_END -->",
    re.DOTALL,
)


@lru_cache(maxsize=1)
def load_review_rulings() -> dict:
    """Fail closed if the owner policy is absent or malformed."""
    match = _BLOCK.search(REVIEW_PATH.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError("REVIEW.md is missing its owner-rulings block")
    rulings = json.loads(match.group(1))
    if not isinstance(rulings, dict):
        raise ValueError("Owner rulings must be an object")
    aliases = rulings.get("currency_aliases")
    if not isinstance(aliases, list) or not aliases or any(
            not isinstance(group, list) or len(group) < 2 or
            any(not isinstance(marker, str) or not marker for marker in group)
            for group in aliases):
        raise ValueError("Owner rulings need currency alias groups")
    for name in ("missing_currency_marker_is_different", "column_bare_value_allowed",
                 "trim_trailing_punctuation", "expand_weekday_month_abbreviations",
                 "number_words_equal_digits"):
        if type(rulings.get(name)) is not bool:
            raise ValueError(f"Owner rulings need an explicit {name} decision")
    lines = rulings.get("judge_prompt_lines")
    if not isinstance(lines, list) or not lines or any(
            not isinstance(line, str) or not line.strip() for line in lines):
        raise ValueError("Owner rulings need judge prompt instructions")
    return rulings
