"""The Day 2 measurement selects text-layer documents without document-specific paths."""

import json
from pathlib import Path

from src.development_run import run_development


ROOT = Path(__file__).resolve().parents[1]


def test_text_only_mode_runs_fifteen_public_pdfs_offline(tmp_path):
    calls = []

    def recorded(messages):
        calls.append(messages)
        if "top-level keys" in messages[0]["content"]:
            requested = json.loads(messages[1]["content"].split(
                "Requested keyed field names: ", 1)[1].split("\n", 1)[0])
            content = {"fields": {name: {"value": None, "quote": "",
                                         "kind": "labelled_value", "origin": "extracted"}
                                  for name in requested}}
        else:
            content = {"facts": []}
        return {"content": json.dumps(content), "usage": {}, "api_created_at": None,
                "latency_seconds": 0.0}

    run = run_development(root=ROOT, output_root=tmp_path,
                          model_request=recorded, text_only=True)
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    assert summary["documents"] == 15
    assert summary["complete"] is True
    assert all(row["source_mode"] == "text" for row in summary["page_results"])
    assert len(calls) == summary["pages"] * 2
