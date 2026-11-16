"""The CLI accepts confirmed currency metadata without changing key values."""

from pathlib import Path

import pymupdf

from run_eval import load_truth


ROOT = Path(__file__).resolve().parents[1]


def test_cli_loads_all_confirmed_money_keys():
    keys = ROOT / "data" / "ground_truth"
    for key_path in keys.glob("*.json"):
        pdf_path = ROOT / "data" / "pdfs" / (key_path.stem + ".pdf")
        with pymupdf.open(pdf_path) as pdf:
            truth = load_truth(key_path, key_path.stem, len(pdf))
        for field in truth["fields"]:
            if field["type"] == "money":
                assert field["printed_marker"] in {"USD", "CAD", "₹", "$", "none", "₹ and rupees", "₹ and Indian rupees"}
                assert field["currency_basis"] in {"printed", "inferred"}
                assert field["marker_scope"] in {"adjacent", "column", "none"}
                assert field["unit_scale"] in {1, 1000}


def test_owner_approved_document_date_order_is_inherited_by_date_fields():
    key_path = ROOT / "data" / "ground_truth" / "statement_001.json"
    with pymupdf.open(ROOT / "data" / "pdfs" / "statement_001.pdf") as pdf:
        truth = load_truth(key_path, "statement_001", len(pdf))
    assert truth["date_order"] == "DMY"
    assert all(field["date_order"] == "DMY" for field in truth["fields"]
               if field["type"] == "date")


def test_notice_day_first_order_records_owner_context():
    key_path = ROOT / "data" / "ground_truth" / "notice_001.json"
    with pymupdf.open(ROOT / "data" / "pdfs" / "notice_001.pdf") as pdf:
        truth = load_truth(key_path, "notice_001", len(pdf))
    assert truth["date_order"] == "DMY"
    assert truth["date_order_basis"] == "owner_context"
    assert all(field["date_order"] == "DMY" for field in truth["fields"]
               if field["type"] == "date")
