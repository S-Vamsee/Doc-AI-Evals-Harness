"""A model's origin label cannot turn an explicit null into an inferred value."""

import json

import pymupdf

from src.core_pipeline import run_text_page


def test_explicit_null_with_inferred_origin_is_still_scored_as_abstention(tmp_path):
    path = tmp_path / "invoice.pdf"
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Invoice number A-17")
    page.insert_text((72, 92), "Payment due")
    page.insert_text((72, 112), "The payment due field has no date on this specimen.")
    pdf.save(path)
    pdf.close()

    def recorded(messages):
        content = ({"fields": {"due_date": {"value": None, "quote": "",
                                             "origin": "inferred"}}}
                   if "top-level keys" in messages[0]["content"] else {"facts": []})
        return {"content": json.dumps(content), "finish_reason": "stop", "usage": {},
                "api_created_at": None, "latency_seconds": 0.0}

    work = run_text_page("sample_null", path, 1, "https://example.org/invoice.pdf",
                         answer_key={"due_date": {"value": None, "type": "date"}},
                         output_root=tmp_path / "runs", model_request=recorded)
    result = json.loads((work / "result.json").read_text(encoding="utf-8"))
    field = result["scored"]["fields"][0]
    assert result["scored"]["exact_passed"] == 1
    assert field["answer_status"] == "abstention"
    assert field["root_cause"] is None
    assert result["outcome_counts"]["abstentions"] == 1
