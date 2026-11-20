"""Judge-free development measurement across all 20 public documents."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

import pymupdf

from src.model_config import public_model_label
from src.core_pipeline import (KEYED_PROMPT, PUBLIC_MODEL_LABEL, SYSTEM_PROMPT,
                               _code_version, run_text_page)
from src.field_definitions import DEFINITIONS_PATH
from src.vision import vision_cache_signature


ROOT = Path(__file__).resolve().parents[1]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_cached_scan(path: Path, baseline_dir: Path) -> dict:
    saved_path = baseline_dir / f"{path.stem}.json"
    if not saved_path.is_file():
        raise FileNotFoundError(f"Saved scan reading is missing for {path.stem}")
    saved = json.loads(saved_path.read_text(encoding="utf-8"))
    signature = vision_cache_signature(path)
    if saved.get("cache_signature") != signature or not saved.get("pages"):
        raise ValueError(f"Saved scan reading is stale for {path.stem}")
    return {"pages": saved["pages"], "cache_signature": signature, "cache_hit": True}


def run_development(*, root: Path = ROOT, output_root: Path | None = None,
                    model_request=None, scan_loader=load_cached_scan,
                    max_cost_usd: float = 1.0,
                    text_only: bool = False) -> Path:
    """Run every answer-key page; a one-reader scan stays uncertain."""
    root = Path(root)
    if output_root is None:
        output_root = Path(os.getenv("HARNESS_RESULTS_DIR",
                                         str(root / "results" / "environments" / "live-dev")))
    output_root = Path(output_root)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    work = output_root / "development_runs" / run_id
    work.mkdir(parents=True, exist_ok=False)
    sources = {entry["doc_id"]: entry for entry in json.loads(
        (root / "data" / "sources.json").read_text(encoding="utf-8"))}
    pdfs = sorted((root / "data" / "pdfs").glob("*.pdf"))
    if text_only:
        selected = []
        for path in pdfs:
            key_path = root / "data" / "ground_truth" / f"{path.stem}.json"
            fields = json.loads(key_path.read_text(encoding="utf-8"))["fields"]
            keyed_pages = sorted({field["page"] for field in fields})
            with pymupdf.open(path) as pdf:
                if all(len(pdf[number - 1].get_text(sort=True).strip()) >= 40
                       for number in keyed_pages):
                    selected.append(path)
        pdfs = selected
    manifest = {"environment": "live-dev", "run_id": run_id,
                "selection": "text_only" if text_only else "all_public_documents",
                "model_label": public_model_label(),
                "prompt_sha256": hashlib.sha256(
                    (KEYED_PROMPT + "\n" + SYSTEM_PROMPT + "\n").encode("utf-8") +
                    DEFINITIONS_PATH.read_bytes()).hexdigest(),
                "field_definitions_sha256": hashlib.sha256(
                    DEFINITIONS_PATH.read_bytes()).hexdigest(),
                "code_version": _code_version(), "documents": [], "pages": []}
    rows = []
    failures = []
    total_cost = 0.0
    from run_eval import load_truth

    for pdf_path in pdfs:
        doc_id = pdf_path.stem
        key_path = root / "data" / "ground_truth" / f"{doc_id}.json"
        try:
            with pymupdf.open(pdf_path) as pdf:
                page_count = len(pdf)
            truth = load_truth(key_path, doc_id, page_count)
            source = sources[doc_id]
            if truth["source_url"] != source["source_url"] or not truth[
                    "source_url"].startswith("https://"):
                raise ValueError("Answer key and public source URL disagree")
            pages_to_run = sorted({field["page"] for field in truth["fields"]})
            manifest["documents"].append({
                "doc_id": doc_id, "source_url": truth["source_url"],
                "pdf_sha256": _sha(pdf_path), "answer_key_sha256": _sha(key_path),
                "keyed_pages": pages_to_run,
            })
            cached = None
            for page_number in pages_to_run:
                with pymupdf.open(pdf_path) as pdf:
                    has_text = len(pdf[page_number - 1].get_text(sort=True).strip()) >= 40
                override = None
                signature = None
                if not has_text:
                    if cached is None:
                        cached = scan_loader(pdf_path, root / "results" / "ocr")
                        cache_copy = output_root / "ocr" / f"{doc_id}.json"
                        cache_copy.parent.mkdir(parents=True, exist_ok=True)
                        _write(cache_copy, cached)
                    override = cached["pages"][page_number - 1]
                    signature = cached["cache_signature"]
                key = {field["field"]: {name: value for name, value in field.items()
                                         if name not in {"field", "page"}}
                       for field in truth["fields"] if field["page"] == page_number}
                page_work = run_text_page(
                    doc_id, pdf_path, page_number, truth["source_url"],
                    answer_key=key, document_type=source["type"],
                    output_root=work / "pages", model_request=model_request,
                    page_text_override=override, ocr_cache_signature=signature,
                )
                result = json.loads((page_work / "result.json").read_text(encoding="utf-8"))
                if not result["complete"]:
                    failures.append({"doc_id": doc_id, "page": page_number,
                                     "failure": result["failures"][0]})
                page_manifest = page_work / "manifest.json"
                if page_manifest.is_file():
                    manifest["pages"].append({
                        "doc_id": doc_id, "page": page_number,
                        "manifest": str(page_manifest.relative_to(work)),
                        "prompt_sha256": json.loads(page_manifest.read_text(
                            encoding="utf-8"))["prompt_sha256"],
                    })
                row = {"doc_id": doc_id, "page": page_number,
                       "source_mode": result.get("source_mode", "unknown"),
                       "complete": result["complete"],
                       "call_status": result.get("call_status"),
                       "open_overlap_count": len(result.get("open_overlaps", [])),
                       "open_fact_count": sum(record.get("source_call") == "open"
                                              for record in result.get("records", [])),
                       "counts": result.get("counts"),
                       "scored_fields": (result.get("scored") or {}).get("scored"),
                       "exact_passed": (result.get("scored") or {}).get("exact_passed"),
                       "judge_scoring_enabled": False,
                       "reference_cost_usd_estimate": result.get(
                           "reference_cost_usd_estimate", 0.0),
                       "latency_seconds": result.get("latency_seconds"),
                       "run_folder": str(page_work.relative_to(work))}
                rows.append(row)
                total_cost += row["reference_cost_usd_estimate"] or 0.0
                print(f"{doc_id} page {page_number}: " + (
                    "complete" if result["complete"] else "incomplete"), flush=True)
                if total_cost > max_cost_usd:
                    failures.append({"stage": "spend_limit", "reason":
                                     "Running hosted estimate exceeded the owner limit"})
                    break
            if total_cost > max_cost_usd:
                break
        except Exception as exc:
            failures.append({"doc_id": doc_id, "stage": "input_or_ocr",
                             "reason": f"{type(exc).__name__}: {exc}"})
            print(f"{doc_id}: incomplete at input_or_ocr", flush=True)
    summary = {"complete": not failures and len(manifest["documents"]) == len(pdfs),
               "documents": len(manifest["documents"]), "pages": len(rows),
               "judge_calls": 0, "page_results": rows, "failures": failures,
               "reference_cost_usd_estimate": round(total_cost, 8)}
    _write(work / "manifest.json", manifest)
    _write(work / "summary.json", summary)
    lines = ["# Development run", "", f"Run: {run_id}; environment: live-dev; "
             f"model label: {public_model_label()}; judge calls: 0.",
             f"Documents attempted: {summary['documents']} of {len(pdfs)}; "
             f"keyed pages: {summary['pages']}; complete: {summary['complete']}.",
             f"Hosted token-rate reference estimate: ${total_cost:.6f}; billed cost unverified.",
             "", "| Document | Page | Source | Keyed call | Open call | Open facts (experimental) | Open overlaps | Facts | Verified | Uncertain | Failed | Exact |",
             "| --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in rows:
        counts = row["counts"] or {}
        exact = f"{row['exact_passed']}/{row['scored_fields']}" if row[
            "scored_fields"] is not None else "unscored"
        lines.append(f"| {row['doc_id']} | {row['page']} | {row['source_mode']} | "
                     f"{'complete' if (row['call_status'] or {}).get('keyed', {}).get('complete') else 'incomplete'} | "
                     f"{'complete' if (row['call_status'] or {}).get('open', {}).get('complete') else 'incomplete'} | "
                     f"{row['open_fact_count']} | "
                     f"{row['open_overlap_count']} | "
                     f"{counts.get('facts_in', 0)} | {counts.get('verified', 0)} | "
                     f"{counts.get('uncertain', 0)} | {counts.get('failed', 0)} | {exact} |")
    if failures:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {json.dumps(item, ensure_ascii=False)}" for item in failures)
    (work / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return work


def compare_development_runs(old: Path, new: Path) -> dict:
    """Compare keyed fields only after checking all fixed inputs and code."""
    old, new = Path(old), Path(new)
    left = json.loads((old / "manifest.json").read_text(encoding="utf-8"))
    right = json.loads((new / "manifest.json").read_text(encoding="utf-8"))

    def identity(manifest: dict) -> dict:
        return {"code_version": manifest["code_version"],
                "prompt_sha256": manifest["prompt_sha256"],
                "documents": manifest["documents"],
                "pages": [{"doc_id": item["doc_id"], "page": item["page"],
                           "prompt_sha256": item["prompt_sha256"]}
                          for item in manifest["pages"]]}

    if identity(left) != identity(right):
        raise ValueError("Development comparison needs identical inputs, prompts, and code")

    def fields(folder: Path) -> tuple[dict, dict]:
        summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
        if not summary["complete"]:
            raise ValueError("Development comparison needs two complete runs")
        found = {}
        for page in summary["page_results"]:
            result = json.loads((folder / page["run_folder"] / "result.json").read_text(
                encoding="utf-8"))
            for item in result["scored"]["fields"]:
                found[(page["doc_id"], page["page"], item["field"])] = item
        return found, summary

    before, old_summary = fields(old)
    after, new_summary = fields(new)
    if before.keys() != after.keys():
        raise ValueError("Development comparison needs the same keyed fields")
    counts = {"better": 0, "worse": 0, "unchanged": 0, "changed_no_flip": 0}
    changes = []
    for doc_id, page, field in sorted(before):
        prior, current = before[(doc_id, page, field)], after[(doc_id, page, field)]
        if prior["exact"] == current["exact"] and prior["extracted"] == current["extracted"]:
            counts["unchanged"] += 1
            continue
        if prior["exact"] == "fail" and current["exact"] == "pass":
            direction = "better"
        elif prior["exact"] == "pass" and current["exact"] == "fail":
            direction = "worse"
        else:
            direction = "changed_no_flip"
        counts[direction] += 1
        changes.append({"doc_id": doc_id, "page": page, "field": field,
                        "direction": direction, "old_exact": prior["exact"],
                        "new_exact": current["exact"],
                        "old_value": prior["extracted"],
                        "new_value": current["extracted"]})
    def totals(summary: dict) -> dict:
        return {name: sum((page.get("counts") or {}).get(name, 0)
                          for page in summary["page_results"])
                for name in ("facts_in", "verified", "uncertain", "failed", "skipped")}
    return {"identical_inputs": True, "old_run": old.name, "new_run": new.name,
            "keyed_fields": len(before), **counts, "changes": changes,
            "old_counts": totals(old_summary), "new_counts": totals(new_summary)}

