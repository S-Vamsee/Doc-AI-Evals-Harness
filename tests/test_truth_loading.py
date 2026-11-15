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
