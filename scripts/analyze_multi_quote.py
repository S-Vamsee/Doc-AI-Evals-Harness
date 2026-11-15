"""Audit saved multi-location quote outcomes without changing evidence rules."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import sys


REASON = "The quote occurs in multiple places."


def _space(value: object) -> str:
    return " ".join(str(value).casefold().split())


def classify_quote(record: dict) -> str:
    quote = _space(record["evidence"]["quote"])
    value = _space(record.get("value") or "")
    if record.get("kind") in {"statement", "line_item"}:
        return "statement_or_row"
    if quote == value:
        return "bare_value"
    without_currency = re.sub(r"^(?:[$₹£€]|usd|inr|cad|eur)\s*", "", quote)
    if without_currency == value:
        return "bare_value"
    if value and value in quote and len(quote) > len(value):
        return "label_and_value"
    return "other_or_unresolved"


def phrase_occurrences(page_text: str, quote: str) -> int:
    normalized_page = _space(page_text)
    normalized_quote = _space(quote)
    return normalized_page.count(normalized_quote) if normalized_quote else 0


def analyze_run(folder: Path) -> dict:
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    by_class = Counter()
    repeated = Counter()
    source_calls = Counter()
    examples = []
    for row in summary["page_results"]:
        page_folder = folder / row["run_folder"]
        result = json.loads((page_folder / "result.json").read_text(encoding="utf-8"))
        if not result.get("records"):
            continue
        page_text = (page_folder / "page_text.txt").read_text(encoding="utf-8")
        for record in result["records"]:
            if record.get("reason") != REASON:
                continue
            category = classify_quote(record)
            occurrences = phrase_occurrences(page_text, record["evidence"]["quote"])
            by_class[category] += 1
            repeated["two_or_more" if occurrences >= 2 else
                     "one" if occurrences == 1 else "none_in_normalized_text"] += 1
            if category == "label_and_value" and occurrences >= 2:
                repeated["repeated_label_and_value"] += 1
            source_calls[record.get("source_call") or "unspecified"] += 1
            if len(examples) < 8:
                examples.append({"doc_id": row["doc_id"], "relation": record["relation"],
                                 "category": category, "normalized_text_occurrences": occurrences,
                                 "quote": record["evidence"]["quote"]})
    return {"run_id": folder.name, "total": sum(by_class.values()),
            "categories": dict(by_class), "text_occurrences": dict(repeated),
            "source_calls": dict(source_calls), "examples": examples}


def render(runs: list[dict]) -> str:
    lines = ["# Saved multi-location quote audit", "",
             "This audit reads existing page results and page text. It does not change the "
             "evidence rule or make model calls. `label_and_value` means the quote contains "
             "the value plus other printed words; it does not prove the words name the right role.",
             "", "| Measure | Run 1 | Run 2 | Run 3 |", "| --- | ---: | ---: | ---: |"]
    def row(name, getter):
        lines.append("| " + name + " | " + " | ".join(str(getter(run)) for run in runs) + " |")
    row("Run ID", lambda run: run["run_id"])
    row("Multiple-location outcomes", lambda run: run["total"])
    for name in ("bare_value", "label_and_value", "statement_or_row", "other_or_unresolved"):
        row(name.replace("_", " ").capitalize(),
            lambda run, name=name: run["categories"].get(name, 0))
    for name in ("two_or_more", "one", "none_in_normalized_text", "repeated_label_and_value"):
        row("Normalized page-text occurrences: " + name.replace("_", " "),
            lambda run, name=name: run["text_occurrences"].get(name, 0))
    lines.extend(["", "A PDF text search can return several rectangles for one long "
                  "printed phrase. The `one` row is therefore distinct from a phrase "
                  "actually repeated in the normalized page text. This classification "
                  "is an audit aid, not a new verification rule.", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("Usage: analyze_multi_quote.py RUN1 RUN2 RUN3 OUTPUT.md")
    runs = [analyze_run(Path(folder)) for folder in sys.argv[1:4]]
    output = Path(sys.argv[4])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(runs), encoding="utf-8")
    output.with_suffix(".json").write_text(json.dumps(runs, indent=2, ensure_ascii=False) + "\n",
                                            encoding="utf-8")
    print(output)
