"""Markdown summary of a completed evaluation run."""

from __future__ import annotations

from src.regression import format_comparison


def make_report(results: dict, comparison: dict | None = None) -> str:
    rows = [
        "| Doc | Model | Fields | Accuracy | Grounded | Reference cost (est.) | Latency |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for doc in results["documents"]:
        if doc["status"] != "ok":
            rows.append(f'| {doc["doc_id"]} | failed | — | — | — | — | — |')
            continue
        grounded = "—" if doc["groundedness"] is None else f'{doc["groundedness"]:.1f}%'
        rows.append(
            f'| {doc["doc_id"]} | {doc["model"]} | {doc["fields"]} | '
            f'{doc["accuracy"]:.1f}% | {grounded} | '
            f'${doc["cost_usd_estimate"]:.6f} | {doc["latency_seconds"]:.2f}s |'
        )
    aggregate = results["aggregate"]
    grounded = "—" if aggregate["groundedness"] is None else f'{aggregate["groundedness"]:.1f}%'
    rows.append(
        f'| **Overall** | — | {aggregate["fields"]} | {aggregate["accuracy"]:.1f}% | '
        f'{grounded} | ${aggregate["cost_usd_estimate"]:.6f} total | '
        f'{aggregate["mean_latency_seconds"]:.2f}s avg |'
    )
    sections = ["# Evaluation results", "", f'Run: {results["run_at_utc"]}', "", *rows, "", "## Failures", ""]
    failures = []
    for doc in results["documents"]:
        if doc["status"] != "ok":
            failures.append(f'- **{doc["doc_id"]}**: {doc["error"]}')
            continue
        for item in doc["failures"]:
            failures.append(
                f'- **{doc["doc_id"]} / {item["field"]}**: expected '
                f'`{item["expected"]}`, got `{item["got"]}`'
            )
        for item in doc["ungrounded"]:
            failures.append(
                f'- **{doc["doc_id"]} / {item["field"]}**: `{item["got"]}` '
                "was not found in the extracted PDF text"
            )
    sections.extend(failures or ["None."])
    if any(doc.get("field_scores") for doc in results["documents"]):
        sections.extend([
            "", "## Field verdicts", "",
            "| Doc | Field | Exact | Judge | Grounded |",
            "| --- | --- | --- | --- | --- |",
        ])
        for doc in results["documents"]:
            for item in doc.get("field_scores", []):
                exact = "pass" if item["exact_match"] else "fail"
                judge = "—" if item["judge_match"] is None else ("pass" if item["judge_match"] else "fail")
                grounded = "—" if item["grounded"] is None else ("yes" if item["grounded"] else "no")
                sections.append(f'| {doc["doc_id"]} | {item["field"]} | {exact} | {judge} | {grounded} |')
    sections.append("")
    if comparison is not None:
        sections.extend(["", format_comparison(comparison).rstrip(), ""])
    return "\n".join(sections)
