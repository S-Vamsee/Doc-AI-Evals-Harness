"""Compare saved development fields across code versions, without model calls."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_field_map(folder: Path) -> tuple[dict, dict]:
    summary = _read(folder / "summary.json")
    manifest = _read(folder / "manifest.json")
    found = {}
    for page in summary["page_results"]:
        result = _read(folder / page["run_folder"] / "result.json")
        details = (result.get("scored") or {}).get("fields")
        if details is None:
            truth = _read(ROOT / "data" / "ground_truth" / f"{page['doc_id']}.json")
            failure = (result.get("failures") or [{}])[0]
            details = [{"field": field["field"], "exact": "fail", "extracted": None,
                        "root_cause": {"stage": failure.get("stage", "unknown"),
                                       "reason": failure.get("reason", "incomplete")}}
                       for field in truth["fields"] if field["page"] == page["page"]]
        for detail in details:
            key = (page["doc_id"], page["page"], detail["field"])
            if key in found:
                raise ValueError(f"Repeated keyed field in run: {key}")
            found[key] = detail
    return found, manifest


def compare_field_maps(old: dict, new: dict) -> dict:
    if old.keys() != new.keys():
        raise ValueError("Daily comparison needs the same keyed fields")
    counts = {"better": 0, "worse": 0, "unchanged": 0, "changed_no_flip": 0}
    changes = []
    for doc_id, page, field in sorted(old):
        before, after = old[(doc_id, page, field)], new[(doc_id, page, field)]
        if before["exact"] == after["exact"] and before["extracted"] == after["extracted"]:
            counts["unchanged"] += 1
            continue
        if before["exact"] == "fail" and after["exact"] == "pass":
            direction = "better"
        elif before["exact"] == "pass" and after["exact"] == "fail":
            direction = "worse"
        else:
            direction = "changed_no_flip"
        counts[direction] += 1
        changes.append({"doc_id": doc_id, "page": page, "field": field,
                        "direction": direction, "old_exact": before["exact"],
                        "new_exact": after["exact"],
                        "old_value": before["extracted"],
                        "new_value": after["extracted"],
                        "root_cause": after.get("root_cause")})
    return {"keyed_fields": len(old), "counts": counts, "changes": changes,
            "worse": [item for item in changes if item["direction"] == "worse"]}


def align_to_new_fields(old: dict, new: dict) -> dict:
    """Select the old fields measured in a narrower new run."""
    if not new.keys() <= old.keys():
        raise ValueError("New run has keyed fields absent from the old run")
    return {key: old[key] for key in new}


def compare_runs(old_folder: Path, new_folder: Path, *, text_subset: bool = False) -> dict:
    old, old_manifest = load_field_map(old_folder)
    new, new_manifest = load_field_map(new_folder)
    def inputs(manifest):
        return {item["doc_id"]: (item["pdf_sha256"], item["answer_key_sha256"])
                for item in manifest["documents"]}
    old_inputs, new_inputs = inputs(old_manifest), inputs(new_manifest)
    if text_subset:
        old = align_to_new_fields(old, new)
        old_inputs = {doc_id: old_inputs.get(doc_id) for doc_id in new_inputs}
    if old_inputs != new_inputs:
        raise ValueError("PDF or answer-key bytes changed across days")
    result = compare_field_maps(old, new)
    result.update({"old_run": old_folder.name, "new_run": new_folder.name,
                   "input_hashes_identical": True,
                   "text_subset": text_subset,
                   "code_identical": old_manifest["code_version"] == new_manifest["code_version"],
                   "prompt_identical": old_manifest["prompt_sha256"] == new_manifest["prompt_sha256"]})
    return result


def render(result: dict) -> str:
    counts = result["counts"]
    lines = ["# Day 2 versus Day 1 development fields", "",
             f"Old run: `{result['old_run']}`. New run: `{result['new_run']}`.",
             f"The same {result['keyed_fields']} human-keyed fields and identical PDF/key bytes "
             "were compared. Code and prompt changed, so this is a cross-version impact "
             "comparison, not a repeated-run stability estimate.", "",
             f"Better: {counts['better']}; worse: {counts['worse']}; "
             f"unchanged: {counts['unchanged']}; value changed without pass/fail flip: "
             f"{counts['changed_no_flip']}.", "", "## Worse fields", "",
             "| Document | Page | Field | Old value | New value | Earliest root-cause stage | Reason |",
             "| --- | ---: | --- | --- | --- | --- | --- |"]
    for item in result["worse"]:
        cause = item.get("root_cause") or {}
        def cell(value):
            return str(value if value is not None else "null").replace("|", "\\|").replace("\n", " ")
        lines.append("| " + " | ".join(cell(value) for value in (
            item["doc_id"], item["page"], item["field"], item["old_value"],
            item["new_value"], cause.get("stage", "unassigned"),
            cause.get("reason", "unassigned"))) + " |")
    lines.extend(["", "The comparison covers the keyed fields in the new run. "
                  "The extraction contract and code changed between runs; the field-level "
                  "differences show the measured impact of those changes.", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) not in (4, 5) or (len(sys.argv) == 5 and sys.argv[4] != "--text-subset"):
        raise SystemExit("Usage: compare_daily.py OLD_RUN NEW_RUN OUTPUT.md [--text-subset]")
    comparison = compare_runs(Path(sys.argv[1]), Path(sys.argv[2]),
                              text_subset=len(sys.argv) == 5)
    output = Path(sys.argv[3])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(comparison), encoding="utf-8")
    output.with_suffix(".json").write_text(
        json.dumps(comparison, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(output)
