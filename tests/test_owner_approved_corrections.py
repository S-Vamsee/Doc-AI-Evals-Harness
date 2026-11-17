"""An owner-approved semantic correction stays visible against the old key."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_symptom_value_excludes_the_printed_specimen_marking():
    data = json.loads((ROOT / "data/ground_truth/form_handwritten_001.json").read_text(encoding="utf-8"))
    symptom = next(item for item in data["fields"] if item["field"] == "symptoms")
    assert symptom["value"] == "mild headache"
    assert symptom["page"] == 1
    correction = json.loads((ROOT / "data/calibration/owner_approved_key_corrections.json").read_text(
        encoding="utf-8"))[0]
    assert correction["doc_id"] == "form_handwritten_001"
    assert correction["field"] == "symptoms"
    assert correction["old_value"] == "mild headache, SAMPLE only"
    assert correction["new_value"] == "mild headache"
    assert correction["owner_approved"] is True


def test_owner_corrections_remove_form_descriptor_and_signature_sample_mark():
    key = json.loads((ROOT / "data/ground_truth/form_handwritten_001.json").read_text(
        encoding="utf-8"))
    values = {item["field"]: item["value"] for item in key["fields"]}
    assert values["instruction"] == "rest and hydrate"
    assert values["signature"] == "J. Rivera"
    corrections = json.loads((ROOT / "data/calibration/owner_approved_key_corrections.json")
                             .read_text(encoding="utf-8"))
    by_field = {item["field"]: item for item in corrections}
    assert by_field["instruction"]["old_value"] == "rest and hydrate — fictional clinic form"
    assert by_field["instruction"]["new_value"] == "rest and hydrate"
    assert by_field["signature"]["old_value"] == "J. Rivera (SAMPLE)"
    assert by_field["signature"]["new_value"] == "J. Rivera"
    assert all(by_field[name]["owner_approved"] is True
               for name in ("instruction", "signature"))
