"""The owner sheet must be balanced, source-backed, and blind to the answer."""

from collections import Counter
from decimal import Decimal
from pathlib import Path
import csv
import re

from src.calibration_sheet import CASES, build_sheet, verify_public_pdf_quotes


ROOT = Path(__file__).resolve().parents[1]


def test_requested_mix_and_document_coverage():
    assert len(CASES) == 60
    assert Counter(case.group for case in CASES) == {
        "identical": 12, "equivalent": 16, "plausible_wrong": 22, "borderline": 10,
    }
    assert len({case.doc_id for case in CASES}) >= 15
    assert sum(case.field.endswith(("amount", "balance", "due", "cap", "rate"))
               or case.field in {"gross_profit_2024_thousands", "net_income_2024_thousands"}
               for case in CASES) >= 12
    assert all(case.source_quotes for case in CASES)


def test_owner_sheet_has_neutral_shuffled_ids_and_no_answer_hints():
    result = build_sheet(ROOT)
    pairs = result["pairs"]
    assert len(pairs) == 60
    assert len({pair["pair_id"] for pair in pairs}) == 60
    assert all(re.fullmatch(r"P-\d{6}", pair["pair_id"]) for pair in pairs)
    assert all(pair["human_label"] is None for pair in pairs)
    assert all("proposed_match" not in pair and "judge_match" not in pair
               and "group" not in pair and "change" not in pair for pair in pairs)
    assert all(pair["source_url"].startswith("https://") for pair in pairs)
    assert all(not str(pair["candidate"]).endswith(" X") for pair in pairs)
    assert len({pair["doc_id"] for pair in pairs[:10]}) >= 6


def test_candidates_are_not_duplicate_rows_for_same_field():
    pairs = build_sheet(ROOT)["pairs"]
    signatures = [(pair["doc_id"], pair["field"], str(pair["candidate"]))
                  for pair in pairs]
    assert len(signatures) == len(set(signatures))


def test_unfounded_source_excerpt_is_rejected():
    pair = build_sheet(ROOT)["pairs"][0]
    broken = dict(pair)
    broken["source_quotes"] = [{"page": 1, "quote": "THIS QUOTE IS NOT IN THE PDF"}]
    import pytest

    with pytest.raises(ValueError, match="Source quote missing"):
        verify_public_pdf_quotes(ROOT, [broken])


def test_three_one_digit_confusions_are_backed_by_different_documents():
    def digits(value, value_type):
        if value_type == "money":
            number = Decimal(re.sub(r"[^\d.]", "", str(value)))
            return re.sub(r"\D", "", f"{number:.2f}")
        return re.sub(r"\D", "", str(value))

    documents = set()
    for pair in build_sheet(ROOT)["pairs"]:
        if pair["value_type"] not in {"money", "free_text"}:
            continue
        left = digits(pair["reference"], pair["value_type"])
        right = digits(pair["candidate"], pair["value_type"])
        if left and len(left) == len(right) and sum(a != b for a, b in zip(left, right)) == 1:
            documents.add(pair["doc_id"])
    assert len(documents) >= 3


def test_two_column_owner_label_template_is_safe_for_editing():
    path = ROOT / "data" / "calibration" / "owner_labels.csv"
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 60
    assert set(rows[0]) == {"pair_id", "human_label_true_or_false"}
    assert {row["pair_id"] for row in rows} == {
        pair["pair_id"] for pair in build_sheet(ROOT)["pairs"]}
    assert all(row["human_label_true_or_false"].strip().casefold() in
               {"", "true", "false"} for row in rows)
