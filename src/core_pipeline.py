"""One text-page run through the rule-tested, machine-first evaluation core."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import time

import pymupdf
from openai import OpenAI

from src.policy import (FactRecord, build_extraction_messages, make_manifest,
                        render_policy_report, score_records, validate_tally,
                        verify_text_record)
from src.review import build_review_queue
from src.score import estimated_cost


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results" / "experiments" / "core_runs"
PUBLIC_MODEL_LABEL = "deepseek-flash"
SYSTEM_PROMPT = (
    "Read one PDF page and list its distinct structured facts as JSON. Return an object "
    "with a facts array. Every fact needs kind, subject (string or null), "
    "relation (a short snake_case name), value (exact printed text or null), origin "
    "(extracted or inferred), and quote (a short exact, contiguous excerpt from the page). "
    "Kinds are party, identifier, date_or_time, amount, line_item, labelled_value, "
    "statement, and unclassified. The most specific kind wins: use party, identifier, "
    "date_or_time, or amount whenever one fits. Use labelled_value only for a "
    "label-and-value pair that fits none of those four. A line_item is one table row "
    "as one fact; include its columns as an object of printed column names and string values. "
    "A statement is a sentence that asserts something. Nothing is dropped: record "
    "anything that fits no kind as unclassified. Use the exact requested relation "
    "name once for each requested field. "
    "Use null and an empty quote when a requested field is absent. Also list other useful "
    "facts on the page without repeating the requested fields. Copy currency markers and "
    "identifiers exactly. Never calculate, fill gaps, or invent values. Return JSON only."
)


def _write(path: Path, value: dict | list) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _live_request(messages: list[dict]) -> dict:
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key or key == "your_key_here":
        raise RuntimeError("DEEPSEEK_API_KEY is missing from the ignored .env file")
    model = os.getenv("DEEPSEEK_MODEL", PUBLIC_MODEL_LABEL)
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    client = OpenAI(api_key=key, base_url=base_url, timeout=180)
    request = {"model": model, "messages": messages, "temperature": 0,
               "response_format": {"type": "json_object"}, "max_tokens": 10000}
    if base_url.rstrip("/") == "https://api.deepseek.com":
        request["extra_body"] = {"thinking": {"type": "disabled"}}
    started = time.perf_counter()
    response = client.chat.completions.create(**request)
    usage = response.usage
    return {
        "content": response.choices[0].message.content or "",
        "finish_reason": response.choices[0].finish_reason,
        "usage": {"prompt_tokens": usage.prompt_tokens if usage else None,
                  "completion_tokens": usage.completion_tokens if usage else None,
                  "prompt_cache_hit_tokens": getattr(usage, "prompt_cache_hit_tokens", None),
                  "prompt_cache_miss_tokens": getattr(usage, "prompt_cache_miss_tokens", None)},
        "api_created_at": response.created,
        "latency_seconds": round(time.perf_counter() - started, 3),
    }


def _code_version(root: Path = ROOT) -> str:
    paths = [root / "run_eval.py", *sorted((root / "src").glob("*.py")),
             root / "scripts" / "environments.py",
             root / "data" / "calibration" / "REVIEW.md"]
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(root)).replace("\\", "/").encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _cell(value: object) -> str:
    return str(value if value is not None else "null").replace("|", "\\|").replace("\n", " ")


def _report(result: dict, document_type: str) -> str:
    lines = [render_policy_report(counts=result["counts"],
                                  document_types={document_type: 1},
                                  failures=result["failures"],
                                  scored=result["scored"]).rstrip(),
             "", f"Source: {result['source_url']}",
             f"Page: {result['page_number']}; source mode: {result['source_mode']}; "
             f"model: {PUBLIC_MODEL_LABEL}; "
             f"judge: disabled; extraction cache: no.",
             f"Extraction latency: {result['latency_seconds']:.3f}s; "
             f"reference API cost estimate: ${result['reference_cost_usd_estimate']:.6f}.",
             "", "## Keyed fields", "",
             "| Field | Expected | Extracted | Exact |", "| --- | --- | --- | --- |"]
    if result["scored"]:
        for field in result["scored"]["fields"]:
            lines.append(f"| {_cell(field['field'])} | {_cell(field['expected'])} | "
                         f"{_cell(field['extracted'])} | {field['exact']} |")
    else:
        lines.append("No human key was supplied; all extracted facts are unscored.")
    lines.extend(["", "## All extracted facts", "",
                  "| ID | Kind | Subject | Relation | Value | Columns | Origin | Page | Quote | Box | State | Reason | Exact |",
                  "| --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- |"])
    for fact in result["records"]:
        ev = fact["evidence"]
        lines.append("| " + " | ".join(_cell(value) for value in (
            fact["fact_id"], fact["kind"], fact["subject"], fact["relation"],
            fact["value"], fact.get("columns"), fact["origin"], ev["page"], ev["quote"], ev["bbox"],
            fact["state"], fact["reason"], fact["exact"])) + " |")
    lines.extend(["", "## Review queue", "",
                  f"Possible near-matches: {result['review_counts']['possible_near_matches']}; "
                  f"other uncertain facts shown: {result['review_counts']['uncertain']}; "
                  f"verified sample: {result['review_counts']['verified_sample']}; "
                  f"uncovered text lines: {result['review_counts']['uncovered_text']}.",
                  "Human verdicts: pending. Exact failures stay failed after review.",
                  f"Unclassified facts: {result['kind_counts'].get('unclassified', 0)}.",
                  "", "Manifest: `manifest.json`; structured output: `result.json`; "
                  "review items: `review.json`."])
    return "\n".join(lines) + "\n"


def run_text_page(doc_id: str, pdf_path: Path, page_number: int, source_url: str, *,
                  answer_key: dict | None = None, document_type: str = "document",
                  output_root: Path | None = None, model_request=None,
                  page_text_override: str | None = None,
                  ocr_cache_signature: str | None = None) -> Path:
    """Write a complete or explicitly incomplete one-page run; never call a judge."""
    if not source_url.startswith("https://"):
        raise ValueError("A public HTTPS source URL is required")
    if page_number < 1:
        raise ValueError("page_number must be positive")
    if page_text_override is not None and not ocr_cache_signature:
        raise ValueError("A cached scan reading needs its checked cache signature")
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", doc_id)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    if output_root is None:
        selected = os.getenv("HARNESS_RESULTS_DIR")
        output_root = Path(selected) / "experiments" / "core_runs" if selected else DEFAULT_OUTPUT
    work = Path(output_root) / safe_id / run_id
    work.mkdir(parents=True, exist_ok=False)
    source_mode = "cached_scan" if page_text_override is not None else "text"
    stage = "ocr" if source_mode == "cached_scan" else "text_layer"
    manifest = None
    try:
        pdf_bytes = Path(pdf_path).read_bytes()
        with pymupdf.open(pdf_path) as pdf:
            if page_number > len(pdf):
                raise ValueError("Requested page is outside the PDF")
            page = pdf[page_number - 1]
            text = (page_text_override if page_text_override is not None
                    else page.get_text(sort=True)).strip()
            if len(text) < 40:
                raise ValueError("Page has no usable text layer")
            requested = list(answer_key or {})
            user = ("Requested keyed field names: " + json.dumps(requested) +
                    "\nThe answer values are not provided.\nPAGE TEXT:\n" + text)
            messages = build_extraction_messages(user, SYSTEM_PROMPT)
            manifest = make_manifest(model_label=PUBLIC_MODEL_LABEL,
                                     prompt=json.dumps(messages, ensure_ascii=False,
                                                       sort_keys=True),
                                     pdf_bytes=pdf_bytes, code_version=_code_version(),
                                     cache_steps={"extraction": False, "evidence": False,
                                                  "vision": source_mode == "cached_scan"})
            manifest.update({"doc_id": doc_id, "page_number": page_number,
                             "environment": os.getenv("HARNESS_ENV", "unlabelled"),
                             "source_mode": source_mode,
                             "ocr_cache_signature": ocr_cache_signature,
                             "source_url": source_url, "page_text_sha256": hashlib.sha256(
                                 text.encode("utf-8")).hexdigest(),
                             "answer_key_sha256": hashlib.sha256(json.dumps(
                                 answer_key, sort_keys=True, ensure_ascii=False).encode("utf-8")
                             ).hexdigest() if answer_key is not None else None,
                             "judge_scoring_enabled": False})
            _write(work / "manifest.json", manifest)
            (work / "page_text.txt").write_text(text + "\n", encoding="utf-8")
            stage = "extraction"
            reply = (model_request or _live_request)(messages)
            raw = reply["content"]
            (work / "extraction.raw.json").write_text(raw + "\n", encoding="utf-8")
            if reply.get("finish_reason") == "length":
                raise ValueError("Extractor response hit its output limit; raw JSON was saved")
            extracted = json.loads(raw)
            if not isinstance(extracted, dict) or not isinstance(extracted.get("facts"), list):
                raise ValueError("Extractor did not return a facts array")
            records = []
            for index, item in enumerate(extracted["facts"], 1):
                if not isinstance(item, dict):
                    raise ValueError(f"Fact {index} is not an object")
                value = item.get("value")
                columns = item.get("columns")
                if item.get("kind") == "line_item" and isinstance(value, dict):
                    if columns is None:
                        columns = value
                    value = item.get("quote")
                if isinstance(columns, dict):
                    columns = {str(name): str(entry) for name, entry in columns.items()}
                if value is not None and not isinstance(value, (str, int, float)):
                    raise ValueError(f"Fact {index} has an invalid value")
                missing_columns = item.get("kind") == "line_item" and not columns
                records.append(FactRecord.model_validate({
                    "fact_id": f"f{index:03d}", "kind": item.get("kind"),
                    "subject": item.get("subject"), "relation": item.get("relation"),
                    "value": str(value) if value is not None else None,
                    "columns": columns,
                    "origin": item.get("origin"),
                    "evidence": {"page": page_number, "quote": item.get("quote"),
                                 "bbox": None},
                    "state": "failed" if missing_columns else "uncertain",
                    "reason": ("Line item is missing table columns."
                               if missing_columns else "Evidence has not been checked."),
                    "stage": "extraction" if missing_columns else "none",
                    "exact": "unscored", "judge": "unscored",
                    "human_verdict": None,
                }))
            stage = "evidence_check"
            if source_mode == "cached_scan":
                checked = [record if record.state == "failed" else FactRecord.model_validate({
                    **record.model_dump(), "state": "uncertain", "stage": "ocr",
                    "reason": "A cached scan reading lacks independent OCR verification.",
                }) for record in records]
            else:
                checked = [verify_text_record(record, page) for record in records]
        stage = "answer_key"
        scored = score_records(checked, answer_key)
        exact_by_field = {detail["field"]: detail["exact"] for detail in scored["fields"]}
        checked = [FactRecord.model_validate({**record.model_dump(),
                                              "exact": exact_by_field.get(record.relation,
                                                                           "unscored")})
                   for record in checked]
        counts = {"facts_in": len(checked), "verified": sum(x.state == "verified" for x in checked),
                  "uncertain": sum(x.state == "uncertain" for x in checked),
                  "failed": sum(x.state == "failed" for x in checked), "skipped": 0}
        validate_tally(counts)
        stage = "report"
        queue = build_review_queue(checked, text, scored=scored)
        _write(work / "review.json", queue)
        usage = reply.get("usage") or {}
        created = reply.get("api_created_at")
        cost = estimated_cost(usage, created)[0] if created is not None and usage.get(
            "prompt_tokens") is not None and usage.get("completion_tokens") is not None else 0.0
        result = {"complete": True, "exit_code": 0, "doc_id": doc_id,
                  "source_url": source_url, "page_number": page_number,
                  "source_mode": source_mode,
                  "records": [record.model_dump() for record in checked], "counts": counts,
                  "kind_counts": {kind: sum(record.kind == kind for record in checked)
                                  for kind in ("party", "identifier", "date_or_time", "amount",
                                               "line_item", "labelled_value", "statement",
                                               "unclassified")},
                  "scored": scored, "failures": [], "usage": usage,
                  "latency_seconds": float(reply.get("latency_seconds", 0.0)),
                  "reference_cost_usd_estimate": cost,
                  "review_counts": {name: len(queue[name]) for name in
                                    ("possible_near_matches", "uncertain",
                                     "verified_sample", "uncovered_text")}}
        _write(work / "result.json", result)
        (work / "report.md").write_text(_report(result, document_type), encoding="utf-8")
        return work
    except Exception as exc:
        failure = {"stage": stage, "attempt": 1,
                   "reason": f"{type(exc).__name__}: {exc}"}
        result = {"complete": False, "exit_code": 1, "doc_id": doc_id,
                  "source_url": source_url, "page_number": page_number,
                  "failures": [failure]}
        _write(work / "result.json", result)
        (work / "report.md").write_text(
            f"# Incomplete one-page run\n\nStage: {stage}\nReason: {failure['reason']}\n",
            encoding="utf-8")
        return work
