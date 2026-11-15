"""A missing printed box label is reported at the earliest available stage."""

import json
from pathlib import Path

from src.core_pipeline import run_text_page


ROOT = Path(__file__).resolve().parents[1]


def test_w2_missing_labels_are_text_layer_root_causes(tmp_path):
    def recorded(messages):
        if "top-level keys" in messages[0]["content"]:
            payload = {"fields": {
                "tax_year": {"value": None, "quote": "", "kind": "date_or_time"},
                "federal_income_tax_withheld": {"value": "1,160.00",
                                                "quote": "1,160.00", "kind": "amount"},
            }}
        else:
            payload = {"facts": []}
        return {"content": json.dumps(payload), "usage": {}, "api_created_at": None,
                "latency_seconds": 0.0}

    run = run_text_page("w2_001", ROOT / "data/pdfs/w2_001.pdf", 1,
                        "https://epaystubs.net/pdfs/W2_ORD6AEC6730533E5.pdf",
                        answer_key={"tax_year": {"value": 2026, "type": "number"},
                                    "federal_income_tax_withheld": {"value": 9200,
                                                                    "type": "money"}},
                        model_request=recorded, output_root=tmp_path / "runs")
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    causes = {item["field"]: item["root_cause"] for item in result["scored"]["fields"]}
    assert causes["tax_year"]["stage"] == "text_layer"
    assert causes["federal_income_tax_withheld"]["stage"] == "text_layer"
