"""Compare two saved evaluation runs without calling a model."""

from __future__ import annotations


def compare_runs(previous: dict, current: dict) -> dict:
    old_docs = {doc["doc_id"]: doc for doc in previous["documents"] if doc["status"] == "ok"}
    new_docs = {doc["doc_id"]: doc for doc in current["documents"] if doc["status"] == "ok"}
    flips = []
    for doc_id in sorted(old_docs.keys() & new_docs.keys()):
        old_fields = {item["field"]: item for item in old_docs[doc_id].get("field_scores", [])}
        new_fields = {item["field"]: item for item in new_docs[doc_id].get("field_scores", [])}
        for field in sorted(old_fields.keys() & new_fields.keys()):
            for metric in ("exact_match", "judge_match"):
                old_pass = old_fields[field].get(metric)
                new_pass = new_fields[field].get(metric)
                if old_pass is not None and new_pass is not None and old_pass != new_pass:
                    flips.append({
                        "doc_id": doc_id,
                        "field": field,
                        "metric": "exact" if metric == "exact_match" else "judge",
                        "from": "pass" if old_pass else "fail",
                        "to": "pass" if new_pass else "fail",
                    })
    old_total = previous["aggregate"]
    new_total = current["aggregate"]
    return {
        "previous_run": previous["run_at_utc"],
        "current_run": current["run_at_utc"],
        "accuracy_delta_points": round(new_total["accuracy"] - old_total["accuracy"], 2),
        "cost_delta_usd_estimate": round(
            new_total["cost_usd_estimate"] - old_total["cost_usd_estimate"], 8
        ),
        "mean_latency_delta_seconds": round(
            new_total["mean_latency_seconds"] - old_total["mean_latency_seconds"], 3
        ),
        "added_documents": sorted(new_docs.keys() - old_docs.keys()),
        "removed_documents": sorted(old_docs.keys() - new_docs.keys()),
        "flips": flips,
        "regression": bool(old_docs.keys() - new_docs.keys())
        or new_total["accuracy"] < old_total["accuracy"] or any(
            item["from"] == "pass" for item in flips
        ),
    }


def format_comparison(comparison: dict) -> str:
    lines = [
        "## Regression comparison",
        "",
        f'Previous: {comparison["previous_run"]}',
        f'Current: {comparison["current_run"]}',
        "",
        f'Accuracy: {comparison["accuracy_delta_points"]:+.2f} percentage points',
        f'Reference cost: ${comparison["cost_delta_usd_estimate"]:+.6f}',
        f'Mean latency: {comparison["mean_latency_delta_seconds"]:+.3f}s',
        f'Regression detected: {"yes" if comparison["regression"] else "no"}',
        f'Added documents: {", ".join(comparison["added_documents"]) or "none"}',
        f'Removed documents: {", ".join(comparison["removed_documents"]) or "none"}',
        "",
        "### Field changes",
        "",
    ]
    if comparison["flips"]:
        lines.extend(
            f'- {item["doc_id"]} / {item["field"]} ({item["metric"]}): {item["from"]} -> {item["to"]}'
            for item in comparison["flips"]
        )
    else:
        lines.append("No pass/fail changes among fields scored in both runs.")
    return "\n".join(lines) + "\n"
