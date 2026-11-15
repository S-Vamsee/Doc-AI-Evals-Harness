"""A cached scan reading can be extracted but cannot verify itself."""

import json

import pymupdf

from src.core_pipeline import run_text_page


def test_cached_scan_stays_uncertain_without_independent_ocr(tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    pdf = pymupdf.open()
    pdf.new_page()
    pdf.save(pdf_path)
    pdf.close()
    text = "Invoice number INV-4102. Vendor Northvale Paper Supply. Total $128.40."

    def recorded(_messages):
        return {"content": json.dumps({"facts": [{
            "kind": "identifier", "subject": None, "relation": "invoice_number",
            "value": "INV-4102", "origin": "extracted", "quote": "Invoice number INV-4102"
        }, {
            "kind": "line_item", "subject": None, "relation": "bad_row",
            "value": "Vendor Northvale", "origin": "extracted", "quote": "Vendor Northvale"
        }]}), "usage": {}, "api_created_at": None, "latency_seconds": 0.0}

    run = run_text_page("scan", pdf_path, 1, "https://example.org/scan.pdf",
                        page_text_override=text, ocr_cache_signature="checked-signature",
                        output_root=tmp_path / "runs", model_request=recorded)
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert result["complete"] is True
    assert result["source_mode"] == "cached_scan"
    assert result["counts"] == {"facts_in": 2, "verified": 0,
                                "uncertain": 1, "failed": 1, "skipped": 0}
    assert "independent" in result["records"][0]["reason"].lower()
    assert result["records"][1]["state"] == "failed"
    assert result["records"][1]["stage"] == "extraction"
    assert manifest["cache_steps"]["vision"] is True
    assert manifest["ocr_cache_signature"] == "checked-signature"

