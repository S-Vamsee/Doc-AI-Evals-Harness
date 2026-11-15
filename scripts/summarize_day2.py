"""Summarize saved Day 2 runs without making model calls."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_run(folder: Path) -> dict:
    folder = Path(folder)
    summary = _read(folder / "summary.json")
    manifest = _read(folder / "manifest.json")
    states = Counter({name: 0 for name in ("verified", "uncertain", "failed",
                                           "skipped", "abstentions", "role_not_printed")})
    reasons = Counter()
    field_failures = Counter()
    root_causes = Counter()
    passed = total = complete_pages = unscored_due_incomplete = 0
    value_passed = keyed_complete_pages = open_complete_pages = 0
    open_overlaps = open_disagreements = inferred_keyed = 0
    for row in summary["page_results"]:
        result = _read(folder / row["run_folder"] / "result.json")
        complete_pages += bool(result["complete"])
        call_status = result.get("call_status") or {}
        keyed_complete_pages += bool((call_status.get("keyed") or {}).get("complete"))
        open_complete_pages += bool((call_status.get("open") or {}).get("complete"))
        overlaps = result.get("open_overlaps") or []
        open_overlaps += len(overlaps)
        open_disagreements += sum(item.get("disagrees") is True for item in overlaps)
        for name in ("verified", "uncertain", "failed", "skipped"):
            states[name] += (result.get("counts") or {}).get(name, 0)
        for name in ("abstentions", "role_not_printed"):
            states[name] += (result.get("outcome_counts") or {}).get(name, 0)
        scored = result.get("scored") or {}
        passed += scored.get("exact_passed", 0)
        value_passed += scored.get("value_passed", scored.get("exact_passed", 0))
        total += scored.get("scored", 0)
        if not scored and row.get("doc_id") and row.get("page"):
            key_path = ROOT / "data" / "ground_truth" / f"{row['doc_id']}.json"
            entry = next((item for item in manifest.get("documents", [])
                          if item["doc_id"] == row["doc_id"]), None)
            if entry and hashlib.sha256(key_path.read_bytes()).hexdigest() != entry[
                    "answer_key_sha256"]:
                raise ValueError(f"Answer key changed after run: {row['doc_id']}")
            expected_count = sum(field["page"] == row["page"]
                                 for field in _read(key_path)["fields"])
            total += expected_count
            unscored_due_incomplete += expected_count
            failure = (result.get("failures") or [{}])[0]
            root_causes[(failure.get("stage", "unknown"),
                         failure.get("reason", "incomplete page"))] += expected_count
        for record in result.get("records", []):
            inferred_keyed += (record.get("source_call") == "keyed"
                               and record.get("origin") == "inferred")
            if record["state"] == "uncertain" and record["value"] is not None:
                reasons[record["reason"]] += 1
        for failure in result.get("failures", []):
            field_failures[(failure.get("stage", "unknown"),
                            failure.get("reason", "unknown"))] += 1
        for field in scored.get("fields", []):
            cause = field.get("root_cause")
            if cause:
                root_causes[(cause["stage"], cause["reason"])] += 1
    return {"run_id": folder.name, "documents": summary["documents"],
            "pages": summary["pages"], "complete_pages": complete_pages,
            "keyed_complete_pages": keyed_complete_pages,
            "open_complete_pages": open_complete_pages,
            "open_overlaps": open_overlaps,
            "open_disagreements": open_disagreements,
            "inferred_keyed": inferred_keyed,
            "value_passed": value_passed,
            "unscored_due_incomplete": unscored_due_incomplete,
            "keyed": {"passed": passed, "total": total},
            "states": dict(states), "uncertain_reasons": dict(reasons),
            "field_failures": {f"{stage}: {reason}": count
                               for (stage, reason), count in field_failures.items()},
            "root_causes": {f"{stage}: {reason}": count
                            for (stage, reason), count in root_causes.items()},
            "code_version": manifest["code_version"],
            "prompt_sha256": manifest["prompt_sha256"],
            "selection": manifest["selection"],
            "reference_cost_usd_estimate": summary["reference_cost_usd_estimate"]}


def render(runs: list[dict]) -> str:
    if len(runs) != 3:
        raise ValueError("Day 2 comparison needs exactly three runs")
    if len({(run["code_version"], run["prompt_sha256"], run["selection"])
            for run in runs}) != 1:
        raise ValueError("Runs differ in code, prompt, or selection")
    complete = all(run["complete_pages"] == run["pages"] for run in runs)
    status = ("All three runs completed." if complete else
              "Some pages were incomplete; their keyed failures remain in the score denominator.")
    lines = ["# Day 2: three text-PDF runs", "",
             "These are 15 public text-layer PDFs with 17 keyed pages per run. "
             "Scores count only human-keyed fields. " + status, "",
             "| Measure | Run 1 | Run 2 | Run 3 |", "| --- | ---: | ---: | ---: |"]
    def row(name, getter):
        lines.append("| " + name + " | " + " | ".join(str(getter(run)) for run in runs) + " |")
    row("Run ID", lambda run: run["run_id"])
    row("Keyed exact score", lambda run: f"{run['keyed']['passed']}/{run['keyed']['total']} "
        f"({run['keyed']['passed']/run['keyed']['total']*100:.1f}%)" if run["keyed"]["total"] else "0/0")
    row("Complete pages", lambda run: f"{run['complete_pages']}/{run['pages']}")
    row("Keyed calls complete", lambda run: f"{run['keyed_complete_pages']}/{run['pages']}")
    row("Open calls complete", lambda run: f"{run['open_complete_pages']}/{run['pages']}")
    row("Open overlaps", lambda run: run["open_overlaps"])
    row("Open/keyed value disagreements", lambda run: run["open_disagreements"])
    row("Inferred keyed facts", lambda run: run["inferred_keyed"])
    row("Value matches (including inferred)",
        lambda run: f"{run['value_passed']}/{run['keyed']['total']}")
    row("Keyed fields failed on incomplete page",
        lambda run: run["unscored_due_incomplete"])
    for name in ("verified", "uncertain", "failed", "skipped", "abstentions",
                 "role_not_printed"):
        qualifier = " (subset of uncertain)" if name == "role_not_printed" else (
            " (subset of skipped)" if name == "abstentions" else "")
        row(name.replace("_", " ").capitalize() + qualifier,
            lambda run, name=name: run["states"][name])
    row("Recorded field failures", lambda run: sum(run["field_failures"].values()))
    row("Reference token-rate estimate (USD)",
        lambda run: f"${run['reference_cost_usd_estimate']:.6f}")
    lines.extend(["", "## Reasons for uncertain facts", "",
                  "| Reason | Run 1 | Run 2 | Run 3 |", "| --- | ---: | ---: | ---: |"])
    for reason in sorted(set().union(*(run["uncertain_reasons"] for run in runs))):
        row(reason.replace("|", "\\|"),
            lambda run, reason=reason: run["uncertain_reasons"].get(reason, 0))
    for title, key in (("Extraction failures", "field_failures"),
                       ("Keyed failure root causes", "root_causes")):
        lines.extend(["", f"## {title}", "",
                      "| Stage and reason | Run 1 | Run 2 | Run 3 |",
                      "| --- | ---: | ---: | ---: |"])
        for reason in sorted(set().union(*(run[key] for run in runs))):
            row(reason.replace("|", "\\|"),
                lambda run, reason=reason, key=key: run[key].get(reason, 0))
    lines.extend(["", f"Code version: `{runs[0]['code_version']}`. "
                  f"Prompt SHA-256: `{runs[0]['prompt_sha256']}`.",
                  "Role hint is lexical word overlap only; it is not semantic role verification.",
                  "The five scanned PDFs were outside this text-only measurement.", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("Usage: summarize_day2.py RUN1 RUN2 RUN3 OUTPUT.md")
    selected = [summarize_run(Path(name)) for name in sys.argv[1:4]]
    destination = Path(sys.argv[4])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render(selected), encoding="utf-8")
    destination.with_suffix(".json").write_text(
        json.dumps(selected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(destination)
