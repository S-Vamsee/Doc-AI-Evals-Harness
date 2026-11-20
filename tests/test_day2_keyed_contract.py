"""A keyed reply must distinguish abstention, omission, and duplication."""

import pytest
import json
import pymupdf

from src.core_pipeline import parse_keyed_response, run_text_page


def test_keyed_reply_classifies_each_requested_name():
    raw = ('{"fields":{"invoice_number":{"value":"A-17","quote":"Invoice number A-17"},'
           '"due_date":{"value":null,"quote":""},'
           '"invoice_number":{"value":"A-18","quote":"Invoice number A-18"}}}')
    values, failures = parse_keyed_response(raw, ["invoice_number", "due_date", "vendor_name"])
    assert values["due_date"]["value"] is None
    assert failures == [
        {"field": "invoice_number", "stage": "extraction", "reason": "duplicate"},
        {"field": "vendor_name", "stage": "extraction", "reason": "field omitted"},
    ]


def test_invalid_keyed_shape_is_an_extraction_failure():
    with pytest.raises(ValueError, match="keyed field"):
        parse_keyed_response('{"facts":[]}', ["invoice_number"])


def test_omitted_and_duplicate_fields_are_named_failures_in_saved_run(tmp_path):
    path = tmp_path / "invoice.pdf"
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Invoice number A-17 and vendor Northvale Paper Supply")
    pdf.save(path)
    pdf.close()

    def recorded(messages):
        if "top-level keys" in messages[0]["content"]:
            content = ('{"fields":{"invoice_number":{"value":"A-17",'
                       '"quote":"Invoice number A-17","kind":"identifier"},'
                       '"invoice_number":{"value":"A-17",'
                       '"quote":"Invoice number A-17","kind":"identifier"}}}')
        else:
            content = '{"facts":[]}'
        return {"content": content, "usage": {}, "api_created_at": None,
                "latency_seconds": 0.0}

    run = run_text_page("invoice", path, 1, "https://example.org/invoice.pdf",
                        answer_key={"invoice_number": {"value": "A-17", "type": "identifier"},
                                    "vendor_name": {"value": "Northvale Paper Supply", "type": "name"}},
                        model_request=recorded, output_root=tmp_path / "runs")
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    assert result["complete"] is False and result["exit_code"] == 1
    assert {(item["field"], item["stage"], item["reason"])
            for item in result["failures"]} == {
                ("invoice_number", "extraction", "duplicate"),
                ("vendor_name", "extraction", "field omitted"),
            }
    assert all(item["exact"] == "fail" for item in result["scored"]["fields"])
    assert "incomplete" in (run / "report.md").read_text(encoding="utf-8").lower()


def test_unrequested_field_is_ignored_and_flagged_without_losing_answers():
    raw = ('{"invoice_number": {"value": "A-17", "quote": "Invoice A-17"}, '
           '"origin": "extracted"}')
    warnings = []
    values, failures = parse_keyed_response(raw, ["invoice_number"], warnings)
    assert values["invoice_number"]["value"] == "A-17" and failures == []
    assert warnings == [{"call": "keyed", "stage": "extraction",
                         "reason": "unrequested field ignored: origin"}]


def test_stray_field_in_a_saved_run_is_a_warning_not_a_failure(tmp_path):
    import json
    import pymupdf
    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), "Invoice number A-17 for the supplies delivered")
    path = tmp_path / "page.pdf"
    pdf.save(path)
    pdf.close()

    def reply(messages):
        if "top-level keys" in messages[0]["content"]:
            content = {"invoice_number": {"value": "A-17", "quote": "Invoice number A-17",
                                          "origin": "extracted"}, "origin": "extracted"}
        else:
            content = {"facts": []}
        return {"content": json.dumps(content), "usage": {"prompt_tokens": 5,
                                                          "completion_tokens": 2},
                "api_created_at": 1790000000}

    key = {"invoice_number": {"value": "A-17", "type": "identifier", "prefix_matters": True}}
    run = run_text_page("sample", path, 1, "https://example.org/page.pdf", answer_key=key,
                        output_root=tmp_path / "runs", model_request=reply)
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    assert result["complete"] is True and result["failures"] == []
    assert result["scored"]["exact_passed"] == 1
    assert "unrequested field ignored: origin" in (run / "report.md").read_text(encoding="utf-8")
