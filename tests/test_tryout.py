"""A new document is processed honestly, or refused with a reason, with no answer key."""

import hashlib
import json

import pymupdf
import pytest

import run_eval
from scripts.environments import frozen_heldback
from src.tryout import TryoutRefused, inspect_pdf, parse_fields, run_tryout


def _text_pdf(path, pages=1):
    pdf = pymupdf.open()
    for number in range(pages):
        page = pdf.new_page()
        page.insert_text((72, 72), f"Tender reference TR-20{number}")
        page.insert_text((72, 92), "Closing date 12 March 2027")
        page.insert_text((72, 112), "Issued by Sampleton Works Department")
    pdf.save(path)
    pdf.close()


def _add_image_page(pdf):
    page = pdf.new_page()
    picture = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 40), False)
    picture.clear_with(200)
    page.insert_image(pymupdf.Rect(72, 72, 300, 300), pixmap=picture)


def _reply(content):
    return {"content": json.dumps(content), "usage": {"prompt_tokens": 50, "completion_tokens": 20},
            "api_created_at": 1790000000, "latency_seconds": 0.2, "finish_reason": "stop"}


def _open_reply(messages):
    return _reply({"facts": [
        {"kind": "identifier", "subject": None, "relation": "tender_reference", "value": "TR-200",
         "origin": "extracted", "quote": "Tender reference TR-200"},
        {"kind": "date_or_time", "subject": None, "relation": "closing_date",
         "value": "12 March 2028", "origin": "extracted", "quote": "Closing date 12 March 2028"},
    ]})


def _trace(folder):
    return next(folder.rglob("trace.md")).read_text(encoding="utf-8")


def test_new_text_pdf_gets_a_readable_unscored_trace(tmp_path):
    pdf = tmp_path / "tender.pdf"
    _text_pdf(pdf)
    registry = tmp_path / "registry.json"
    folder = run_tryout(pdf, output_root=tmp_path / "out", registry_path=registry,
                        model_request=_open_reply)
    trace = _trace(folder)
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    for heading in ("## 1. What was read", "## 2. What the model was asked",
                    "## 3. What the model returned", "## 4. What each check decided",
                    "## 5. Final counts", "## 6. Time and estimated cost"):
        assert heading in trace
    assert "Tender reference TR-200" in trace
    assert "[the page text from section 1]" in trace
    assert summary["label"] == "extracted, unscored"
    assert summary["complete"] is True and summary["exit_code"] == 0
    assert next(folder.rglob("open.raw.json")).is_file()
    assert folder.is_relative_to(tmp_path / "out")


def test_tryout_never_reports_an_accuracy_figure(tmp_path):
    pdf = tmp_path / "tender.pdf"
    _text_pdf(pdf)
    folder = run_tryout(pdf, ["tender_reference"], output_root=tmp_path / "out",
                        registry_path=tmp_path / "registry.json",
                        model_request=lambda messages: _reply({"tender_reference": {
                            "value": "TR-200", "quote": "Tender reference TR-200",
                            "origin": "extracted"}})
                        if "top-level keys" in messages[0]["content"] else _open_reply(messages))
    result = json.loads(next(folder.rglob("result.json")).read_text(encoding="utf-8"))
    combined = _trace(folder) + (folder / "summary.md").read_text(encoding="utf-8")
    assert result["scored"]["scored"] == 0 and result["scored"]["accuracy"] is None
    assert result["scored"]["label"] == "extracted, unscored"
    assert "%" not in combined and "exact score" not in combined.casefold()


def test_a_quote_that_is_not_on_the_page_is_uncertain_with_its_reason(tmp_path):
    pdf = tmp_path / "tender.pdf"
    _text_pdf(pdf)
    folder = run_tryout(pdf, output_root=tmp_path / "out", registry_path=tmp_path / "registry.json",
                        model_request=_open_reply)
    result = json.loads(next(folder.rglob("result.json")).read_text(encoding="utf-8"))
    invented = next(item for item in result["records"] if item["relation"] == "closing_date")
    assert invented["state"] == "uncertain"
    assert invented["reason"] in _trace(folder)


def test_named_field_the_model_omits_is_a_recorded_failure(tmp_path):
    pdf = tmp_path / "tender.pdf"
    _text_pdf(pdf)
    folder = run_tryout(pdf, ["tender_reference", "budget"], output_root=tmp_path / "out",
                        registry_path=tmp_path / "registry.json",
                        model_request=lambda messages: _reply({"tender_reference": {
                            "value": "TR-200", "quote": "Tender reference TR-200",
                            "origin": "extracted"}})
                        if "top-level keys" in messages[0]["content"] else _open_reply(messages))
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    assert summary["complete"] is False and summary["exit_code"] == 1
    assert "field omitted" in _trace(folder)


def test_model_failure_is_named_in_the_trace_and_marks_the_run_incomplete(tmp_path):
    pdf = tmp_path / "tender.pdf"
    _text_pdf(pdf)

    def unavailable(messages):
        raise TimeoutError("model did not respond")

    folder = run_tryout(pdf, output_root=tmp_path / "out", registry_path=tmp_path / "registry.json",
                        model_request=unavailable)
    assert json.loads((folder / "summary.json").read_text(encoding="utf-8"))["exit_code"] == 1
    assert "model did not respond" in _trace(folder)


def test_fully_scanned_pdf_is_refused_before_any_model_call(tmp_path):
    path = tmp_path / "scan.pdf"
    pdf = pymupdf.open()
    _add_image_page(pdf)
    pdf.save(path)
    pdf.close()
    registry = tmp_path / "registry.json"

    def must_not_run(messages):
        raise AssertionError("no model call is allowed")

    with pytest.raises(TryoutRefused, match="Day 6"):
        run_tryout(path, output_root=tmp_path / "out", registry_path=registry,
                   model_request=must_not_run)
    assert not registry.exists()


def test_mixed_document_processes_text_and_reports_scan_and_empty_pages(tmp_path):
    path = tmp_path / "mixed.pdf"
    _text_pdf(path, pages=1)
    pdf = pymupdf.open(path)
    _add_image_page(pdf)
    pdf.new_page()
    mixed = tmp_path / "mixed2.pdf"
    pdf.save(mixed)
    pdf.close()
    calls = []

    def counted(messages):
        calls.append(messages)
        return _open_reply(messages)

    folder = run_tryout(mixed, output_root=tmp_path / "out",
                        registry_path=tmp_path / "registry.json", model_request=counted)
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    assert [row["status"] for row in summary["pages"]] == ["complete", "skipped", "empty"]
    assert summary["complete"] is False and len(calls) == 1


@pytest.mark.parametrize("kind", ["missing", "not_pdf", "corrupt", "password"])
def test_unreadable_files_are_refused_with_a_reason(tmp_path, kind):
    path = tmp_path / "bad.pdf"
    if kind == "not_pdf":
        path.write_text("just some notes", encoding="utf-8")
    elif kind == "corrupt":
        path.write_bytes(b"%PDF-1.7\nthis is not really a pdf")
    elif kind == "password":
        pdf = pymupdf.open()
        pdf.new_page().insert_text((72, 72), "Locked document with enough text to read here")
        pdf.save(path, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="reader", owner_pw="owner")
        pdf.close()
    with pytest.raises(TryoutRefused):
        inspect_pdf(path)


def test_registry_keeps_fingerprints_only_and_counts_each_try(tmp_path):
    pdf = tmp_path / "private_name.pdf"
    _text_pdf(pdf)
    registry = tmp_path / "registry.json"
    for _ in range(2):
        run_tryout(pdf, output_root=tmp_path / "out", registry_path=registry,
                   model_request=_open_reply)
    saved = registry.read_text(encoding="utf-8")
    sha256 = hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert json.loads(saved)["documents"][sha256]["tries"] == 2
    assert "private_name" not in saved


def test_a_tried_document_cannot_enter_the_held_back_set(tmp_path):
    sha256 = "a" * 64
    (tmp_path / "data" / "heldback").mkdir(parents=True)
    (tmp_path / "data" / "heldback" / "freeze.json").write_text(
        json.dumps({"frozen": True, "input_sha256": sha256}), encoding="utf-8")
    assert frozen_heldback(tmp_path)["frozen"] is True
    (tmp_path / "data" / "tryout_registry.json").write_text(
        json.dumps({"documents": {sha256: {"tries": 1}}}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="already tried"):
        frozen_heldback(tmp_path)


def test_field_names_are_checked():
    assert parse_fields("total, due_date") == ["total", "due_date"]
    assert parse_fields(None) is None
    for bad in ("", "Total Due", "total,total"):
        with pytest.raises(TryoutRefused):
            parse_fields(bad)


def test_command_line_refuses_a_non_pdf_with_exit_code_two(tmp_path, monkeypatch, capsys):
    path = tmp_path / "notes.txt"
    path.write_text("not a pdf", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["run_eval.py", "--tryout", str(path)])
    assert run_eval.main() == 2
    assert "Refused: Not a PDF file" in capsys.readouterr().err
