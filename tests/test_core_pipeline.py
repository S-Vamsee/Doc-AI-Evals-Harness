"""One text page runs through extraction, code evidence, scoring, and review offline."""

import hashlib
import json

import pymupdf

from src.core_pipeline import run_text_page


def _pdf(path):
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Invoice number A-17")
    page.insert_text((72, 92), "Vendor Northvale")
    page.insert_text((72, 112), "Total amount $128.40")
    pdf.save(path)
    pdf.close()


def _response(messages):
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    return {"content": json.dumps({"facts": [
        {"kind": "field", "subject": None, "relation": "invoice_number",
         "value": "A-17", "origin": "extracted", "quote": "Invoice number A-17"},
        {"kind": "field", "subject": None, "relation": "vendor_name",
         "value": "Northvale", "origin": "extracted", "quote": "Vendor Northvale"},
        {"kind": "field", "subject": None, "relation": "total_amount",
         "value": "128.40", "origin": "extracted", "quote": "Total amount $128.40"},
    ]}), "usage": {"prompt_tokens": 100, "completion_tokens": 80},
            "api_created_at": 1790000000, "latency_seconds": 0.1}


def test_text_page_writes_full_report_manifest_and_near_match_queue(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _pdf(pdf_path)
    key = {
        "invoice_number": {"value": "A-17", "type": "identifier", "prefix_matters": True},
        "vendor_name": {"value": "Northvale", "type": "name"},
        "total_amount": {"value": 128.4, "type": "money", "printed_marker": "$"},
    }
    run = run_text_page("sample", pdf_path, 1, "https://example.org/sample.pdf",
                        answer_key=key, document_type="invoice",
                        output_root=tmp_path / "runs", model_request=_response)
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    queue = json.loads((run / "review.json").read_text(encoding="utf-8"))
    report = (run / "report.md").read_text(encoding="utf-8")
    assert result["complete"] is True
    assert result["counts"] == {"facts_in": 3, "verified": 3,
                                "uncertain": 0, "failed": 0, "skipped": 0}
    assert result["scored"]["exact_passed"] == 2
    assert result["scored"]["judge_accuracy"] is None
    assert queue["possible_near_matches"][0]["field"] == "total_amount"
    assert queue["possible_near_matches"][0]["evidence_state"] == "verified"
    assert result["records"][2]["exact"] == "fail"
    assert result["records"][2]["state"] == "verified"
    assert manifest["input_sha256"] == hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    assert manifest["model_label"] == "deepseek-flash"
    assert manifest["cache_steps"]["extraction"] is False
    assert "2 of 3" in report and "Possible near-matches" in report


def test_extraction_failure_is_saved_as_incomplete_run(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _pdf(pdf_path)

    def timeout(_messages):
        raise TimeoutError("model did not respond")

    run = run_text_page("sample", pdf_path, 1, "https://example.org/sample.pdf",
                        output_root=tmp_path / "runs", model_request=timeout)
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    assert result["complete"] is False
    assert result["failures"][0]["stage"] == "extraction"
    assert "model did not respond" in result["failures"][0]["reason"]
    assert "incomplete" in (run / "report.md").read_text(encoding="utf-8").lower()
