"""Resumable local judge calibration that cannot activate production scoring."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

from src.judge import JUDGE_SYSTEM_PROMPT, judge_pair
from src.policy import calibrate_judge, wilson_interval


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def _owner_labels(path: Path, pairs: list[dict]) -> dict[str, bool]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(pairs) or [row.get("pair_id") for row in rows] != [
            pair.get("pair_id") for pair in pairs]:
        raise ValueError("Owner label IDs or order do not match the review sheet")
    result = {}
    for row in rows:
        label = row.get("human_label_true_or_false", "")
        if label not in {"true", "false"}:
            raise ValueError(f"Missing or invalid owner label for {row['pair_id']}")
        result[row["pair_id"]] = label == "true"
    return result


def run_calibration(pending_path: Path, labels_path: Path, output_path: Path, *,
                    cache_dir: Path, judge_fn=judge_pair,
                    judge_model: str = "gemma3:4b") -> dict:
    """Run all pairs, record failures, and leave judge scoring disabled."""
    pending_path, labels_path, output_path = map(Path, (pending_path, labels_path, output_path))
    cache_dir = Path(cache_dir)
    pending_bytes, labels_bytes = pending_path.read_bytes(), labels_path.read_bytes()
    pairs = json.loads(pending_bytes)["pairs"]
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("Calibration has no pairs")
    code_bytes = Path(__file__).read_bytes() + (Path(__file__).parent / "judge.py").read_bytes()
    result = {
        "status": "running", "judge_scoring_enabled": False,
        "manifest": {
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "extractor_model": "deepseek-flash", "judge_model": judge_model,
            "prompt_sha256": _sha(JUDGE_SYSTEM_PROMPT.encode("utf-8")),
            "input_sha256": _sha(pending_bytes), "labels_sha256": _sha(labels_bytes),
            "code_version": _sha(code_bytes), "cache_hits": 0,
        },
        "verdicts": [], "failures": [],
    }
    try:
        labels = _owner_labels(labels_path, pairs)
    except Exception as exc:
        result["status"] = "incomplete"
        result["failures"].append({"stage": "answer_key", "attempt": 1,
                                   "reason": f"{type(exc).__name__}: {exc}"})
        _write_json(output_path, result)
        return result
    cache_dir.mkdir(parents=True, exist_ok=True)
    for pair in pairs:
        source_excerpt = " | ".join(
            f"p{source['page']}: {source['quote']}" for source in pair["source_quotes"])
        payload = {"field": pair["field"], "reference": pair["reference"],
                   "candidate": pair["candidate"], "source_excerpt": source_excerpt}
        cache_key = _sha(json.dumps({"model": judge_model, "prompt": JUDGE_SYSTEM_PROMPT,
                                     "input": payload}, sort_keys=True,
                                    ensure_ascii=False).encode("utf-8"))
        cache_path = cache_dir / f"{cache_key}.json"
        started = time.perf_counter()
        try:
            if cache_path.is_file():
                verdict = json.loads(cache_path.read_text(encoding="utf-8"))
                used_cache = True
            else:
                verdict = judge_fn(pair["reference"], pair["candidate"],
                                   field=pair["field"], source_excerpt=source_excerpt)
                used_cache = False
            if type(verdict.get("match")) is not bool or not isinstance(verdict.get("reason"), str):
                raise ValueError("Judge verdict is malformed")
            if not used_cache:
                _write_json(cache_path, verdict)
            else:
                result["manifest"]["cache_hits"] += 1
        except Exception as exc:
            result["status"] = "incomplete"
            result["failures"].append({"stage": "judge", "pair_id": pair["pair_id"],
                                       "attempt": 1, "reason": f"{type(exc).__name__}: {exc}"})
            _write_json(output_path, result)
            return result
        result["verdicts"].append({
            "pair_id": pair["pair_id"], "doc_id": pair["doc_id"],
            "field": pair["field"], "reference": pair["reference"],
            "candidate": pair["candidate"], "source_url": pair.get("source_url"),
            "owner_label": labels[pair["pair_id"]], "judge_match": verdict["match"],
            "judge_reason": verdict["reason"], "used_cache": used_cache,
            "latency_seconds": round(time.perf_counter() - started, 3),
        })
        _write_json(output_path, result)
    try:
        calibration = calibrate_judge(
            [{"expected_match": item["owner_label"], "judge_match": item["judge_match"]}
             for item in result["verdicts"]],
            extractor_model="deepseek-flash", judge_model=judge_model)
    except Exception as exc:
        result["status"] = "incomplete"
        result["failures"].append({"stage": "answer_key", "attempt": 1,
                                   "reason": f"{type(exc).__name__}: {exc}"})
        _write_json(output_path, result)
        return result
    result["calibration"] = calibration
    result["disagreements"] = [item for item in result["verdicts"]
                               if item["owner_label"] != item["judge_match"]]
    result["status"] = "awaiting_owner_review"
    result["total_latency_seconds"] = round(sum(item["latency_seconds"]
                                                for item in result["verdicts"]), 3)
    _write_json(output_path, result)
    return result


def render_calibration_report(result: dict) -> str:
    if result.get("status") != "awaiting_owner_review":
        raise ValueError("Cannot report rates from an incomplete calibration")
    data = result["calibration"]

    def rate_line(label: str, count: int, total: int) -> str:
        interval = wilson_interval(count, total)
        return (f"- {label}: {count} of {total} ({count / total * 100:.2f}%; "
                f"95% Wilson interval {interval[0]:.2f}% to {interval[1]:.2f}%).")

    def cell(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = ["# Local judge calibration: owner review required", "",
             f"Calibrated on {data['pairs']} owner-labelled public-document value pairs "
             f"({data['correct_pairs']} same, {data['wrong_pairs']} different). "
             "These rates describe this set only.", "",
             rate_line("False accepts", data["false_accepts"], data["wrong_pairs"]),
             rate_line("False rejects", data["false_rejects"], data["correct_pairs"]),
             "", "Judge scoring is disabled pending owner review.", "",
             f"## Disagreements ({len(result['disagreements'])})", "",
             "| Pair | Document | Field | Reference | Candidate | Owner | Judge | Reason |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for item in result["disagreements"]:
        lines.append("| " + " | ".join(cell(value) for value in (
            item["pair_id"], item["doc_id"], item["field"], item["reference"],
            item["candidate"], item["owner_label"], item["judge_match"],
            item["judge_reason"])) + " |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    model = os.getenv("JUDGE_MODEL", "gemma3:4b")
    report = run_calibration(
        root / "data/calibration/pairs.pending.json",
        root / "data/calibration/owner_labels.csv",
        root / "results/experiments/judge_calibration_pending_review.json",
        cache_dir=root / "results/experiments/judge_cache", judge_model=model)
    if report["status"] == "incomplete":
        raise SystemExit(1)
    (root / "results/experiments/judge_calibration_pending_review.md").write_text(
        render_calibration_report(report), encoding="utf-8")
    print(f"Recorded {len(report['verdicts'])} verdicts; "
          f"{len(report['disagreements'])} disagreements. "
          "Judge scoring remains disabled.")
