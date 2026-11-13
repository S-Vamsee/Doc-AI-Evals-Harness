"""Markdown summary of a completed evaluation run."""

from __future__ import annotations


def make_report(results: dict) -> str:
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
    sections.append("")
    return "\n".join(sections)
