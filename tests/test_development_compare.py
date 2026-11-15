"""A repeated development run reports field flips only on identical inputs."""

import json

import pytest

from src.development_run import compare_development_runs


def _run(folder, value, exact, fingerprint="same"):
    folder.mkdir()
    (folder / "manifest.json").write_text(json.dumps({
        "code_version": fingerprint, "prompt_sha256": "prompt",
        "documents": [{"doc_id": "invoice", "pdf_sha256": "pdf",
                       "answer_key_sha256": "key", "keyed_pages": [1]}],
        "pages": [{"doc_id": "invoice", "page": 1, "prompt_sha256": "request"}],
    }), encoding="utf-8")
    (folder / "summary.json").write_text(json.dumps({
        "complete": True, "documents": 1, "pages": 1, "page_results": [
            {"doc_id": "invoice", "page": 1, "counts": {
                "facts_in": 1, "verified": 1, "uncertain": 0, "failed": 0, "skipped": 0},
             "run_folder": "pages/invoice/one"}],
    }), encoding="utf-8")
    page = folder / "pages" / "invoice" / "one"
    page.mkdir(parents=True)
    (page / "result.json").write_text(json.dumps({
        "scored": {"fields": [{"field": "invoice_number", "extracted": value,
                                "exact": exact}]}}), encoding="utf-8")


def test_compare_reports_worse_field_on_identical_inputs(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    _run(old, "INV-1", "pass")
    _run(new, "INV-2", "fail")
    comparison = compare_development_runs(old, new)
    assert comparison["identical_inputs"] is True
    assert comparison["worse"] == 1
    assert comparison["better"] == 0
    assert comparison["changes"][0]["field"] == "invoice_number"


def test_compare_refuses_different_code_or_inputs(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    _run(old, "INV-1", "pass")
    _run(new, "INV-1", "pass", fingerprint="changed")
    with pytest.raises(ValueError, match="identical"):
        compare_development_runs(old, new)
