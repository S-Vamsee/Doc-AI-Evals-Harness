"""Saved real W-2 replies must not turn a control-number year into extracted evidence."""

import json
from pathlib import Path

from src.core_pipeline import run_text_page


ROOT = Path(__file__).resolve().parents[1]


def test_real_w2_reply_marks_control_number_year_inferred(tmp_path):
    truth = json.loads((ROOT / "data/ground_truth/w2_001.json").read_text(encoding="utf-8"))
    key = {item["field"]: {name: value for name, value in item.items()
                            if name not in {"field", "page"}}
           for item in truth["fields"] if item["page"] == 1}

    def saved(messages):
        name = "day2_w2_keyed.json" if "top-level keys" in messages[0]["content"] else "day2_w2_open.json"
        return {"content": (ROOT / "tests/fixtures" / name).read_text(encoding="utf-8"),
                "finish_reason": "stop", "usage": {}, "api_created_at": None,
                "latency_seconds": 0.0}

    run = run_text_page("w2_001", ROOT / "data/pdfs/w2_001.pdf", 1,
                        truth["source_url"], answer_key=key,
                        model_request=saved, output_root=tmp_path)
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    year = next(item for item in result["records"]
                if item["source_call"] == "keyed" and item["relation"] == "tax_year")
    field = next(item for item in result["scored"]["fields"] if item["field"] == "tax_year")
    assert year["value"] == "2026"
    assert year["evidence"]["quote"] == "QA-W2-2026-01"
    assert year["origin"] == "inferred"
    assert year["state"] != "verified"
    assert field["value_match"] == "pass"
    assert field["exact"] == "fail"
    assert field["answer_status"] == "inferred"
