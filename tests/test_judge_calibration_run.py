"""Calibration records every local verdict and never enables judge scoring itself."""

import csv
import json

from src.judge_calibration_run import run_calibration, render_calibration_report


def inputs(tmp_path):
    pairs = []
    for index in range(60):
        pairs.append({
            "pair_id": f"P-{index:06d}", "doc_id": "public_sample",
            "field": f"total_due_{index}", "reference": "53.78",
            "candidate": "53.78" if index < 24 else "$53.78",
            "source_quotes": [{"page": 1, "quote": "Total due $53.78"}],
            "source_url": "https://example.org/public.pdf",
        })
    pending = tmp_path / "pairs.json"
    pending.write_text(json.dumps({"pairs": pairs}), encoding="utf-8")
    labels = tmp_path / "labels.csv"
    with labels.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["pair_id", "human_label_true_or_false"])
        writer.writerows((pair["pair_id"], "true" if i < 24 else "false")
                         for i, pair in enumerate(pairs))
    return pending, labels


def test_run_is_local_cached_and_awaits_owner_review(tmp_path):
    pending, labels = inputs(tmp_path)
    calls = []

    def judge(reference, candidate, **kwargs):
        calls.append(kwargs)
        return {"match": reference == candidate, "reason": "fixture verdict"}

    output = tmp_path / "run.json"
    cache = tmp_path / "cache"
    result = run_calibration(pending, labels, output, cache_dir=cache,
                             judge_fn=judge, judge_model="gemma3:4b")
    assert result["status"] == "awaiting_owner_review"
    assert result["judge_scoring_enabled"] is False
    assert len(result["verdicts"]) == 60
    assert len(calls) == 60
    assert result["calibration"]["false_accepts"] == 0
    assert result["calibration"]["false_rejects"] == 0
    assert result["manifest"]["prompt_sha256"]
    assert result["manifest"]["labels_sha256"]
    assert result["manifest"]["input_sha256"]
    assert result["manifest"]["code_version"]
    again = run_calibration(pending, labels, output, cache_dir=cache,
                            judge_fn=judge, judge_model="gemma3:4b")
    assert len(calls) == 60
    assert again["manifest"]["cache_hits"] == 60


def test_incomplete_labels_block_judge_calls_and_metrics(tmp_path):
    pending, labels = inputs(tmp_path)
    text = labels.read_text(encoding="utf-8").replace("P-000000,true", "P-000000,")
    labels.write_text(text, encoding="utf-8")
    calls = []

    def judge(*args, **kwargs):
        calls.append(True)
        return {"match": True, "reason": "unused"}

    result = run_calibration(pending, labels, tmp_path / "run.json",
                             cache_dir=tmp_path / "cache", judge_fn=judge,
                             judge_model="gemma3:4b")
    assert result["status"] == "incomplete"
    assert result["judge_scoring_enabled"] is False
    assert "calibration" not in result
    assert result["failures"][0]["stage"] == "answer_key"
    assert not calls


def test_report_lists_every_disagreement_and_both_error_rates():
    result = {
        "status": "awaiting_owner_review", "judge_scoring_enabled": False,
        "calibration": {"pairs": 60, "correct_pairs": 24, "wrong_pairs": 36,
                        "false_accepts": 1, "false_rejects": 1,
                        "false_accept_rate": 1 / 36, "false_reject_rate": 1 / 24},
        "disagreements": [
            {"pair_id": "P-123456", "doc_id": "invoice_001", "field": "total_amount",
             "reference": 53.78, "candidate": "$53.78", "owner_label": False,
             "judge_match": True, "judge_reason": "same number"},
            {"pair_id": "P-654321", "doc_id": "receipt_002", "field": "order_number",
             "reference": "#NV-10482", "candidate": "NV-10482", "owner_label": False,
             "judge_match": True, "judge_reason": "prefix ignored"},
        ],
    }
    report = render_calibration_report(result)
    assert "1 of 36" in report and "1 of 24" in report
    assert "P-123456" in report and "P-654321" in report
    assert "disabled" in report.casefold()
