"""Write a field-level comparison of two complete development runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.development_run import compare_development_runs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = compare_development_runs(args.old, args.new)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "comparison.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Development run comparison", "",
             f"Runs: {result['old_run']} → {result['new_run']}",
             f"Identical inputs, prompts, and code: {result['identical_inputs']}.",
             f"Keyed fields: {result['keyed_fields']}; better: {result['better']}; "
             f"worse: {result['worse']}; unchanged: {result['unchanged']}; "
             f"changed without a score flip: {result['changed_no_flip']}.",
             f"Facts by state, old: {result['old_counts']}; new: {result['new_counts']}.",
             "", "| Document | Page | Field | Change | Old exact | New exact | Old value | New value |",
             "| --- | ---: | --- | --- | --- | --- | --- | --- |"]
    for item in result["changes"]:
        values = [item["doc_id"], item["page"], item["field"], item["direction"],
                  item["old_exact"], item["new_exact"], item["old_value"], item["new_value"]]
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in values) + " |")
    (args.output / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output / "comparison.md")


if __name__ == "__main__":
    main()

