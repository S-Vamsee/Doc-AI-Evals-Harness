"""The 20-document runner stays judge-free and records every keyed page."""

import json
from pathlib import Path

from src.development_run import run_development


ROOT = Path(__file__).resolve().parents[1]


def test_all_development_documents_run_with_recorded_responses(tmp_path):
    requests = []

    def recorded(messages):
        requests.append(messages)
        if "top-level keys" in messages[0]["content"]:
            user = messages[1]["content"]
            requested = json.loads(user.split("Requested keyed field names: ", 1)[1].split("\n", 1)[0])
            content = json.dumps({"fields": {name: {"value": None, "quote": "",
                                                    "kind": "labelled_value", "origin": "extracted"}
                                             for name in requested}})
        else:
            content = '{"facts": []}'
        return {"content": content, "usage": {},
                "api_created_at": None, "latency_seconds": 0.0}

    def cached_scan(_path, _baseline):
        return {"pages": ["Cached public scan text with enough words to pass the page minimum."
                          ] * 3, "cache_signature": "fixture-signature", "cache_hit": True}

    run = run_development(root=ROOT, output_root=tmp_path,
                          model_request=recorded, scan_loader=cached_scan)
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert summary["documents"] == 20
    assert summary["complete"] is True
    assert len(requests) == 2 * summary["pages"]
    assert summary["pages"] >= 20
    assert summary["judge_calls"] == 0
    assert manifest["environment"] == "live-dev"
    assert len(manifest["documents"]) == 20
    assert all(item["pdf_sha256"] and item["answer_key_sha256"]
               for item in manifest["documents"])
    assert any(item["source_mode"] == "cached_scan" for item in summary["page_results"])
    assert all(item["judge_scoring_enabled"] is False for item in summary["page_results"])
    assert all("call_status" in item and "open_overlap_count" in item
               for item in summary["page_results"])
    assert all("open_fact_count" in item for item in summary["page_results"])
    assert "Open facts (experimental)" in (run / "report.md").read_text(encoding="utf-8")

