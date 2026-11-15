"""Replay a saved live invoice response without an API key or network."""

import json
from pathlib import Path

from src.core_pipeline import run_text_page


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def test_saved_live_invoice_reply_reproduces_keyed_score_and_fact_states(tmp_path):
    truth = json.loads((ROOT / "data/ground_truth/invoice_001.json").read_text(encoding="utf-8"))
    key = {item["field"]: {name: value for name, value in item.items()
                            if name not in {"field", "page"}}
           for item in truth["fields"] if item["page"] == 1}
    calls = []

    def recorded(messages):
        calls.append(messages)
        filename = ("day2_invoice_keyed.json" if "top-level keys" in messages[0]["content"]
                    else "day2_invoice_open.json")
        return {"content": (FIXTURES / filename).read_text(encoding="utf-8"),
                "finish_reason": "stop", "usage": {}, "api_created_at": None,
                "latency_seconds": 0.0}

    run = run_text_page("invoice_001", ROOT / "data/pdfs/invoice_001.pdf", 1,
                        truth["source_url"], answer_key=key, output_root=tmp_path,
                        model_request=recorded)
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    assert len(calls) == 2
    assert result["complete"] is True
    assert result["counts"] == {"facts_in": 25, "verified": 5,
                                "uncertain": 20, "failed": 0, "skipped": 0}
    assert result["scored"]["exact_passed"] == result["scored"]["scored"] == 5
    assert (run / "manifest.json").is_file()
    assert (run / "review.json").is_file()
