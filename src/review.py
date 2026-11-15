"""Build a short, auditable human review queue after machine extraction."""

from __future__ import annotations

import random

from src.policy import FactRecord, _plain


def _doubt(record: FactRecord) -> tuple[int, str]:
    if not record.evidence.quote.strip():
        return (0, record.fact_id)
    if record.evidence.bbox is None:
        return (1, record.fact_id)
    return (2, record.fact_id)


def build_review_queue(records: list[FactRecord], page_text: str, *,
                       uncertain_cap: int = 10, sample_size: int = 3,
                       seed: int = 0, scored: dict | None = None) -> dict:
    if uncertain_cap < 0 or sample_size < 0:
        raise ValueError("Review limits cannot be negative")
    if len({record.fact_id for record in records}) != len(records):
        raise ValueError("Duplicate fact IDs in review input")
    by_relation: dict[str, list[FactRecord]] = {}
    for record in records:
        if record.source_call == "open":
            continue
        by_relation.setdefault(record.relation, []).append(record)
    possible_near_matches = []
    queued_ids = set()
    for detail in (scored or {}).get("fields", []):
        if detail.get("exact") != "fail":
            continue
        matches = by_relation.get(detail.get("field"), [])
        if len(matches) != 1:
            continue
        record = matches[0]
        if record.value is None:
            continue
        queued_ids.add(record.fact_id)
        possible_near_matches.append({
            "fact_id": record.fact_id, "field": record.relation,
            "extracted": detail.get("extracted"), "expected": detail.get("expected"),
            "exact": "fail", "review_reason": "possible_near_match",
            "evidence_state": record.state, "evidence": record.evidence.model_dump(),
        })
    uncertain_all = sorted((item for item in records if item.state == "uncertain"
                            and item.value is not None
                            and item.fact_id not in queued_ids), key=_doubt)
    role_all = sorted((item for item in records
                       if item.evidence_support == "role_not_printed" and item.value is not None),
                      key=lambda item: item.fact_id)
    role_sample = random.Random(seed).sample(role_all, min(sample_size, len(role_all)))
    verified_all = sorted((item for item in records if item.state == "verified"
                           and item.fact_id not in queued_ids),
                          key=lambda item: item.fact_id)
    sample = random.Random(seed).sample(verified_all, min(sample_size, len(verified_all)))
    quote_lines = [_plain(part) for record in records for part in record.evidence.quote.splitlines()
                   if part.strip()]
    uncovered = []
    for number, line in enumerate(page_text.splitlines(), 1):
        normalized = _plain(line)
        if normalized and not any(quote in normalized or normalized in quote for quote in quote_lines):
            uncovered.append({"line": number, "text": line})
    return {
        "uncertain": [item.model_dump() for item in uncertain_all[:uncertain_cap]],
        "possible_near_matches": possible_near_matches,
        "verified_sample": [item.model_dump() for item in sample],
        "role_not_printed_sample": [item.model_dump() for item in role_sample],
        "uncovered_text": uncovered,
        "unreviewed_uncertain": max(len(uncertain_all) - uncertain_cap, 0),
        "facts_extracted": len(records),
        "sample_seed": seed,
    }


def apply_human_verdicts(records: list[FactRecord], queue: dict,
                         verdicts: dict[str, str], missing: list[dict]) -> dict:
    offered = {item["fact_id"] for key in ("uncertain", "verified_sample",
                                          "role_not_printed_sample", "possible_near_matches")
               for item in queue.get(key, [])}
    if not set(verdicts).issubset(offered):
        raise ValueError("A verdict names a fact outside the review queue")
    if any(verdict not in {"right", "wrong", "missing"} for verdict in verdicts.values()):
        raise ValueError("Human verdict must be right, wrong, or missing")
    if not isinstance(missing, list) or any(not isinstance(item, dict) or not item.get("relation")
                                            for item in missing):
        raise ValueError("Missing facts need a relation and optional supporting details")
    updated = []
    for record in records:
        data = record.model_dump()
        data["human_verdict"] = verdicts.get(record.fact_id)
        updated.append(FactRecord.model_validate(data))
    sampled = {item["fact_id"] for item in queue["verified_sample"]}
    sample_reviewed = sum(fact_id in sampled for fact_id in verdicts)
    sample_wrong = sum(fact_id in sampled and verdict == "wrong"
                       for fact_id, verdict in verdicts.items())
    return {
        "records": updated,
        "missing_relations": missing,
        "human_reviewed": len(verdicts) + len(missing),
        "facts_extracted": len(records),
        "sample_reviewed": sample_reviewed,
        "sample_wrong": sample_wrong,
        "sample_error_rate": round(sample_wrong / sample_reviewed * 100, 2)
        if sample_reviewed else None,
        "unreviewed_uncertain": queue["unreviewed_uncertain"],
    }
