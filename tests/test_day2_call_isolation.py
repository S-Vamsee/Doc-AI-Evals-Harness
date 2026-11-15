"""Live failure shapes: keyed answers survive open overlap and open-call failure."""

import json

import pymupdf

from src.core_pipeline import run_text_page, _report


def _pdf(path):
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Invoice number A-17")
    page.insert_text((72, 92), "Northvale Paper Supply")
    page.insert_text((72, 112), "Sample invoice for the independent call checks")
    pdf.save(path)
    pdf.close()


def _run(tmp_path, keyed, opened, open_finish="stop"):
    path = tmp_path / "invoice.pdf"
    _pdf(path)

    def recorded(messages):
        is_keyed = "top-level keys" in messages[0]["content"]
        return {"content": keyed if is_keyed else opened,
                "finish_reason": "stop" if is_keyed else open_finish,
                "usage": {}, "api_created_at": None, "latency_seconds": 0.0}

    run = run_text_page("invoice", path, 1, "https://example.org/invoice.pdf",
                        answer_key={"invoice_number": {"value": "A-17", "type": "identifier"},
                                    "vendor_name": {"value": "Northvale Paper Supply", "type": "name"}},
                        model_request=recorded, output_root=tmp_path / "runs")
    return json.loads((run / "result.json").read_text(encoding="utf-8"))


KEYED = json.dumps({"invoice_number": {"value": "A-17", "quote": "Invoice number A-17"},
                    "vendor_name": {"value": "Northvale Paper Supply",
                                    "quote": "Northvale Paper Supply"}})


def test_open_overlap_is_counted_and_cannot_change_keyed_score(tmp_path):
    opened = json.dumps({"facts": [
        {"kind": "identifier", "subject": None, "relation": "invoice_number",
         "value": "A-18", "origin": "extracted", "quote": "Invoice number A-17"},
        {"kind": "party", "subject": None, "relation": "vendor_name",
         "value": "Northvale Paper Supply", "origin": "extracted",
         "quote": "Northvale Paper Supply"},
    ]})
    result = _run(tmp_path, KEYED, opened)
    assert result["complete"] is True
    assert result["scored"]["exact_passed"] == 2
    assert result["failures"] == []
    open_records = [item for item in result["records"] if item["source_call"] == "open"]
    assert len(open_records) == 2
    assert all(item["overlaps_keyed_field"] for item in open_records)
    assert {item["relation"]: item["keyed_disagreement"] for item in open_records} == {
        "invoice_number": True, "vendor_name": False}
    assert all(item["exact"] == "unscored" for item in open_records)
    report = _report(result, "invoice")
    assert "Open overlaps: 2" in report
    assert "invoice_number" in report and "A-18" in report


def test_open_length_failure_preserves_keyed_answers_and_call_status(tmp_path):
    result = _run(tmp_path, KEYED, '{"facts":[', open_finish="length")
    assert result["complete"] is False
    assert result["scored"]["exact_passed"] == 2
    assert result["call_status"]["keyed"]["complete"] is True
    assert result["call_status"]["open"]["complete"] is False
    assert result["failures"][0]["call"] == "open"
    assert result["failures"][0]["stage"] == "extraction"
    assert "open: incomplete" in _report(result, "invoice")


def test_invalid_open_fact_preserves_keyed_answers(tmp_path):
    result = _run(tmp_path, KEYED, '{"facts":[{"kind":"unsupported", "relation":"x"}]}')
    assert result["complete"] is False
    assert result["scored"]["exact_passed"] == 2
    assert result["call_status"]["keyed"]["complete"] is True
    assert result["call_status"]["open"]["complete"] is False
    assert result["failures"][0]["call"] == "open"


def test_keyed_duplicate_keeps_extraction_cause_even_without_role_hint(tmp_path):
    duplicate = ('{"invoice_number":{"value":"A-17","quote":"A-17"},'
                 '"invoice_number":{"value":"A-17","quote":"A-17"},'
                 '"vendor_name":{"value":"Northvale Paper Supply",'
                 '"quote":"Northvale Paper Supply"}}')
    result = _run(tmp_path, duplicate, '{"facts":[]}')
    field = next(item for item in result["scored"]["fields"]
                 if item["field"] == "invoice_number")
    assert field["exact"] == "fail"
    assert field["root_cause"] == {"field": "invoice_number",
                                    "stage": "extraction", "reason": "duplicate"}
