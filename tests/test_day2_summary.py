"""The three-run comparison includes incomplete pages and their uncertainty causes."""

import json

from scripts.summarize_day2 import summarize_run, render


def test_summary_counts_scores_states_and_uncertain_reasons_on_incomplete_page(tmp_path):
    page = tmp_path / "pages" / "sample" / "run"
    page.mkdir(parents=True)
    (page / "result.json").write_text(json.dumps({
        "complete": False, "counts": {"facts_in": 2, "verified": 0,
                                      "uncertain": 1, "failed": 0, "skipped": 1},
        "call_status": {"keyed": {"complete": True}, "open": {"complete": False}},
        "open_overlaps": [{"field": "vendor_name", "disagrees": True}],
        "outcome_counts": {"abstentions": 1, "role_not_printed": 1},
        "scored": {"scored": 2, "exact_passed": 1},
        "records": [{"value": "A-17", "state": "uncertain",
                     "reason": "No printed role label; role hint unavailable."},
                    {"value": None, "state": "uncertain", "reason": "Null answer"}],
        "failures": [{"field": "vendor_name", "stage": "extraction", "reason": "duplicate"}],
    }), encoding="utf-8")
    (tmp_path / "summary.json").write_text(json.dumps({
        "documents": 1, "pages": 1, "page_results": [{"run_folder": "pages/sample/run"}],
        "reference_cost_usd_estimate": 0.01,
    }), encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps({
        "code_version": "abc", "prompt_sha256": "def", "selection": "text_only",
    }), encoding="utf-8")
    result = summarize_run(tmp_path)
    assert result["keyed"] == {"passed": 1, "total": 2}
    assert result["states"] == {"verified": 0, "uncertain": 1, "failed": 0,
                                "skipped": 1, "abstentions": 1,
                                "role_not_printed": 1}
    assert result["uncertain_reasons"] == {
        "No printed role label; role hint unavailable.": 1}
    assert result["keyed_complete_pages"] == 1
    assert result["open_complete_pages"] == 0
    assert result["open_overlaps"] == 1
    assert result["open_disagreements"] == 1


def test_unscored_extraction_failure_keeps_requested_fields_in_denominator(tmp_path):
    page = tmp_path / "pages" / "sample" / "run"
    page.mkdir(parents=True)
    (page / "result.json").write_text(json.dumps({
        "complete": False, "failures": [{"stage": "extraction",
                                         "reason": "output limit"}],
    }), encoding="utf-8")
    (tmp_path / "summary.json").write_text(json.dumps({
        "documents": 1, "pages": 1,
        "page_results": [{"doc_id": "invoice_001", "page": 1,
                          "run_folder": "pages/sample/run"}],
        "reference_cost_usd_estimate": 0.0,
    }), encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps({
        "code_version": "abc", "prompt_sha256": "def", "selection": "text_only",
        "documents": [],
    }), encoding="utf-8")
    result = summarize_run(tmp_path)
    assert result["keyed"]["total"] == 5
    assert result["keyed"]["passed"] == 0
    assert result["unscored_due_incomplete"] == 5


def test_complete_runs_are_not_described_as_incomplete():
    run = {"run_id": "r1", "documents": 15, "pages": 17,
           "complete_pages": 17, "keyed_complete_pages": 17,
           "open_complete_pages": 17, "open_overlaps": 2,
           "open_disagreements": 1, "inferred_keyed": 0,
           "value_passed": 79, "keyed": {"passed": 79, "total": 79},
           "unscored_due_incomplete": 0,
           "states": {name: 0 for name in ("verified", "uncertain", "failed",
                                          "skipped", "abstentions", "role_not_printed")},
           "uncertain_reasons": {}, "field_failures": {}, "root_causes": {},
           "code_version": "abc", "prompt_sha256": "def", "selection": "text_only",
           "reference_cost_usd_estimate": 0.0}
    report = render([run, {**run, "run_id": "r2"}, {**run, "run_id": "r3"}])
    assert "All three runs were incomplete" not in report
