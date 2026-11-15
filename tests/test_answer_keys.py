"""Human keys keep their values except for explicitly owner-approved corrections."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYS = ROOT / "data" / "ground_truth"
ALLOWED_TYPES = {"date", "money", "identifier", "name", "free_text", "number"}


def test_every_human_key_field_has_a_supported_type():
    for path in KEYS.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data["fields"]:
            assert item.get("type") in ALLOWED_TYPES, (path.name, item["field"])
            if item["type"] == "identifier":
                assert isinstance(item.get("prefix_matters"), bool), (path.name, item["field"])


def test_five_documents_include_explicit_human_null_answers():
    with_null = []
    for path in KEYS.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if any(item["value"] is None for item in data["fields"]):
            with_null.append(path.stem)
    assert len(with_null) >= 5, with_null


def test_w2_printed_tax_year_is_kept_as_a_finding():
    data = json.loads((KEYS / "w2_001.json").read_text(encoding="utf-8"))
    years = [item for item in data["fields"] if item["field"] == "tax_year"]
    assert len(years) == 1
    assert years[0]["value"] == 2026


def test_original_human_values_and_pages_are_preserved():
    baseline = json.loads((ROOT / "tests" / "fixtures" / "human_key_baseline.json").read_text(encoding="utf-8"))
    approved = json.loads((ROOT / "data" / "calibration" /
                           "owner_approved_key_corrections.json").read_text(encoding="utf-8"))
    by_approved_field = {(item["doc_id"], item["field"]): item for item in approved}
    assert len(by_approved_field) == len(approved)
    for doc_id, fields in baseline.items():
        current = json.loads((KEYS / f"{doc_id}.json").read_text(encoding="utf-8"))
        by_field = {item["field"]: item for item in current["fields"]}
        for item in fields:
            assert item["field"] in by_field, (doc_id, item["field"])
            correction = by_approved_field.get((doc_id, item["field"]))
            if correction:
                assert correction["owner_approved"] is True
                assert correction["old_value"] == item["value"]
                assert by_field[item["field"]]["value"] == correction["new_value"]
            else:
                assert by_field[item["field"]]["value"] == item["value"], (doc_id, item["field"])
            assert by_field[item["field"]]["page"] == item["page"], (doc_id, item["field"])
