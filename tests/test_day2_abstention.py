"""An explicit null is scored but is not an uncertain fact or review item."""

import json

import pymupdf

from src.core_pipeline import run_text_page


def test_explicit_null_is_scored_as_abstention_and_not_reviewed(tmp_path):
    path = tmp_path / "sample.pdf"
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Invoice number A-17")
    page.insert_text((72, 92), "Payment due")
    page.insert_text((72, 112), "Sample invoice with no printed payment date")
    pdf.save(path)
    pdf.close()

    def reply(messages):
        if "top-level keys" in messages[0]["content"]:
            content = {"fields": {"due_date": {"value": None, "quote": "",
                                               "kind": "date_or_time", "origin": "extracted"}}}
        else:
            content = {"facts": []}
        return {"content": json.dumps(content), "usage": {}, "api_created_at": None,
                "latency_seconds": 0.0}

    run = run_text_page("sample", path, 1, "https://example.org/sample.pdf",
                        answer_key={"due_date": {"value": None, "type": "date"}},
                        output_root=tmp_path / "runs", model_request=reply)
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    queue = json.loads((run / "review.json").read_text(encoding="utf-8"))
    assert result["scored"]["exact_passed"] == 1
    assert result["outcome_counts"]["abstentions"] == 1
    assert result["counts"]["uncertain"] == 0
    assert result["counts"]["skipped"] == 1
    assert queue["uncertain"] == []
    assert queue["possible_near_matches"] == []
