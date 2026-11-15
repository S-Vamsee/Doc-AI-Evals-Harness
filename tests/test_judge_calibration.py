"""A judge is usable only after balanced, independently labelled calibration."""

import pytest

from src.policy import calibrate_judge, score_records


def pairs():
    return ([{"expected_match": True, "judge_match": True} for _ in range(27)]
            + [{"expected_match": True, "judge_match": False} for _ in range(3)]
            + [{"expected_match": False, "judge_match": False} for _ in range(28)]
            + [{"expected_match": False, "judge_match": True} for _ in range(2)])


def test_calibration_reports_both_error_rates_and_counts():
    result = calibrate_judge(pairs(), extractor_model="deepseek-flash", judge_model="gemma3:4b")
    assert result["pairs"] == 60
    assert result["correct_pairs"] == 30
    assert result["wrong_pairs"] == 30
    assert result["false_accepts"] == 2
    assert result["false_rejects"] == 3
    assert result["false_accept_rate"] == pytest.approx(2 / 30)
    assert result["false_reject_rate"] == pytest.approx(3 / 30)


def test_tiny_or_unbalanced_set_cannot_activate_judge():
    with pytest.raises(ValueError):
        calibrate_judge(pairs()[:40], extractor_model="deepseek-flash", judge_model="gemma3:4b")
    with pytest.raises(ValueError):
        calibrate_judge([{"expected_match": True, "judge_match": True}] * 60,
                        extractor_model="deepseek-flash", judge_model="gemma3:4b")


def test_missing_human_label_cannot_activate_judge():
    malformed = pairs()
    malformed[0] = {"judge_match": True}
    with pytest.raises(ValueError):
        calibrate_judge(malformed, extractor_model="deepseek-flash", judge_model="gemma3:4b")


def test_judge_accuracy_is_hidden_without_valid_calibration():
    from tests.test_rules import fact

    answer_key = {"invoice_number": {"value": "A-17", "type": "identifier"}}
    raw = score_records([fact()], answer_key, judge_results={"invoice_number": True})
    assert raw["judge_accuracy"] is None
    assert raw["fields"][0]["judge"] == "unscored"
    metrics = calibrate_judge(pairs(), extractor_model="deepseek-flash", judge_model="gemma3:4b")
    pending = score_records([fact()], answer_key, judge_results={"invoice_number": True},
                            judge_calibration=metrics)
    assert pending["judge_accuracy"] is None
    assert pending["fields"][0]["judge"] == "unscored"
    calibrated = score_records([fact()], answer_key, judge_results={"invoice_number": True},
                               judge_calibration={**metrics, "owner_approved_for_scoring": True})
    assert calibrated["judge_accuracy"] == 100.0
    assert calibrated["false_accept_rate"] == pytest.approx(2 / 30)
    assert calibrated["false_reject_rate"] == pytest.approx(3 / 30)


def test_calibration_file_uses_human_labels_not_proposals(tmp_path):
    import json
    from src.judge import calibrate_file

    raw = []
    for index, pair in enumerate(pairs()):
        raw.append({"pair_id": str(index), "human_label": pair["expected_match"],
                    "proposed_match": not pair["expected_match"],
                    "judge_match": pair["judge_match"]})
    path = tmp_path / "pairs.json"
    path.write_text(json.dumps({"pairs": raw}), encoding="utf-8")
    result = calibrate_file(path, extractor_model="deepseek-flash", judge_model="gemma3:4b")
    assert result["wrong_pairs"] == 30
    assert result["false_accepts"] == 2
    raw[0]["human_label"] = None
    path.write_text(json.dumps({"pairs": raw}), encoding="utf-8")
    with pytest.raises(ValueError, match="human"):
        calibrate_file(path, extractor_model="deepseek-flash", judge_model="gemma3:4b")


def test_review_csv_can_calibrate_without_editing_proposals(tmp_path):
    import csv
    import json
    from src.judge import calibrate_review_csv

    pending = tmp_path / "pending.json"
    rows = []
    labels = pairs()
    for index, pair in enumerate(labels):
        rows.append({"pair_id": str(index), "judge_match": pair["judge_match"],
                     "proposed_match": not pair["expected_match"]})
    pending.write_text(json.dumps({"pairs": rows}), encoding="utf-8")
    review = tmp_path / "review.csv"
    with review.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["pair_id", "human_label_true_or_false"])
        writer.writerows([[index, str(pair["expected_match"]).lower()]
                          for index, pair in enumerate(labels)])
    result = calibrate_review_csv(pending, review, extractor_model="deepseek-flash",
                                  judge_model="gemma3:4b")
    assert result["pairs"] == 60
    assert result["false_accepts"] == 2
    assert all("human_label" not in row for row in rows)
