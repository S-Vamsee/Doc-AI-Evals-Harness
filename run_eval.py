"""Run, calibrate, and compare document evaluations from the CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.extract import extract_facts, read_pdf_pages
from src.judge import judge_document
from src.regression import compare_runs, format_comparison
from src.report import make_report
from src.score import normalize, score_document
from src.vision import has_usable_text, read_scanned_pdf_pages, render_pages, vision_readiness

PDF_DIR = ROOT / "data" / "pdfs"
TRUTH_DIR = ROOT / "data" / "ground_truth"
RESULT_DIR = ROOT / "results"
RUNS_DIR = RESULT_DIR / "runs"
GOLDEN_IDS = ("filing_001", "form_001", "invoice_001", "statement_001", "w2_001")
GOLDEN_CANDIDATES = ROOT / "data" / "golden_candidates.json"


def load_truth(path: Path, doc_id: str, page_count: int) -> dict:
    truth = json.loads(path.read_text(encoding="utf-8"))
    if truth.get("doc_id") != doc_id or not truth.get("source_url"):
        raise ValueError("doc_id or source_url is missing/mismatched")
    fields = truth.get("fields")
    if not isinstance(fields, list) or not 4 <= len(fields) <= 8:
        raise ValueError("Ground truth needs 4–8 manually verified fields")
    names = []
    for item in fields:
        if not isinstance(item, dict) or set(item) != {"field", "value", "page"}:
            raise ValueError("Each field needs exactly field, value, page")
        if not isinstance(item["field"], str) or not item["field"]:
            raise ValueError("Invalid field name")
        if item["value"] is None or isinstance(item["value"], bool) or not isinstance(item["value"], (str, int, float)):
            raise ValueError(f'Invalid truth value for {item["field"]}')
        if not isinstance(item["page"], int) or not 1 <= item["page"] <= page_count:
            raise ValueError(f'Invalid page for {item["field"]}')
        names.append(item["field"])
    if len(names) != len(set(names)):
        raise ValueError("Duplicate ground-truth field names")
    return truth


def aggregate(documents: list[dict]) -> dict:
    successful = [doc for doc in documents if doc["status"] == "ok"]
    fields = sum(doc["fields"] for doc in successful)
    facts = sum(doc["extracted_facts"] for doc in successful)
    judged = [doc for doc in successful if "judge_correct" in doc]
    judge_fields = sum(doc["fields"] for doc in judged)
    judge_correct = sum(doc["judge_correct"] for doc in judged)
    return {
        "documents_ok": len(successful), "documents_failed": len(documents) - len(successful),
        "fields": fields, "correct": sum(doc["correct"] for doc in successful),
        "accuracy": round(sum(doc["correct"] for doc in successful) / fields * 100, 2) if fields else 0,
        "judge_correct": judge_correct,
        "judge_accuracy": round(judge_correct / judge_fields * 100, 2) if judge_fields else None,
        "extracted_facts": facts, "grounded": sum(doc["grounded"] for doc in successful),
        "groundedness": round(sum(doc["grounded"] for doc in successful) / facts * 100, 2) if facts else None,
        "cost_usd_estimate": round(sum(doc["cost_usd_estimate"] for doc in successful), 8),
        "mean_latency_seconds": round(sum(doc["latency_seconds"] for doc in successful) / len(successful), 3) if successful else 0,
        "vision_documents": sum("vision_model" in doc for doc in successful),
        "vision_cached_documents": sum(doc.get("vision_cached", False) for doc in successful),
    }


def calibration_signature() -> str:
    """Invalidate calibration when scoring, the judge, model, or fixed inputs change."""
    code = (ROOT / "src" / "judge.py").read_bytes() + (ROOT / "src" / "score.py").read_bytes()
    config = (
        os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        + "\n"
        + os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
    ).encode("utf-8")
    golden = GOLDEN_CANDIDATES.read_bytes() + b"".join(
        (TRUTH_DIR / f"{doc_id}.json").read_bytes() for doc_id in GOLDEN_IDS
    )
    return hashlib.sha256(code + b"\n" + config + b"\n" + golden).hexdigest()


def calibrate() -> int:
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("Set DEEPSEEK_API_KEY in .env before calibrating.", file=sys.stderr)
        return 2
    candidates = json.loads(GOLDEN_CANDIDATES.read_text(encoding="utf-8"))
    verdicts = []
    for doc_id in GOLDEN_IDS:
        pdf = PDF_DIR / f"{doc_id}.pdf"
        pages = read_pdf_pages(pdf)
        truth = load_truth(TRUTH_DIR / f"{doc_id}.json", doc_id, len(pages))
        extracted = {"fields": candidates[doc_id]}
        if [item["field"] for item in extracted["fields"]] != [item["field"] for item in truth["fields"]]:
            raise ValueError(f"Golden candidate fields differ from answer key for {doc_id}")
        judged = judge_document(extracted, truth, pages)
        for expected, candidate, judge in zip(
            truth["fields"], extracted["fields"], judged["verdicts"], strict=True
        ):
            exact_match = normalize(expected["field"], candidate["value"], expected["value"]) == normalize(
                expected["field"], expected["value"], expected["value"]
            )
            verdicts.append({
                "doc_id": doc_id,
                "field": expected["field"],
                "exact_match": exact_match,
                "judge_match": judge["match"],
                "agree": exact_match == judge["match"],
                "reason": judge["reason"],
            })
        print(f"Calibrated {doc_id}: {sum(item['agree'] for item in verdicts if item['doc_id'] == doc_id)}/{len(truth['fields'])} agreement")
    agreement = sum(item["agree"] for item in verdicts)
    result = {
        "calibrated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "judge_signature": calibration_signature(),
        "golden_fields": len(verdicts),
        "agreements": agreement,
        "passed": len(verdicts) == 26 and agreement >= 25,
        "verdicts": verdicts,
    }
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / "calibration.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Judge agreement: {agreement}/{len(verdicts)}; calibration {'passed' if result['passed'] else 'failed'}")
    return 0 if result["passed"] else 1


def load_calibration() -> dict | None:
    path = RESULT_DIR / "calibration.json"
    if not path.exists():
        return None
    calibration = json.loads(path.read_text(encoding="utf-8"))
    if not calibration.get("passed") or calibration.get("judge_signature") != calibration_signature():
        return None
    return calibration


def run_id(run: dict) -> str:
    stamp = datetime.fromisoformat(run["run_at_utc"])
    pattern = "%Y%m%dT%H%M%S%fZ" if stamp.microsecond else "%Y%m%dT%H%M%SZ"
    return stamp.strftime(pattern)


def save_run_snapshot(run: dict, report: str) -> None:
    folder = RUNS_DIR / run_id(run)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "scores.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    (folder / "report.md").write_text(report, encoding="utf-8")


def show_comparison(previous_id: str) -> int:
    if not re.fullmatch(r"\d{8}T\d{6}(?:\d{6})?Z", previous_id):
        print("Invalid run ID", file=sys.stderr)
        return 2
    old_path = RUNS_DIR / previous_id / "scores.json"
    new_path = RESULT_DIR / "scores.json"
    if not old_path.exists() or not new_path.exists():
        print("Previous or current run is missing", file=sys.stderr)
        return 2
    previous = json.loads(old_path.read_text(encoding="utf-8"))
    current = json.loads(new_path.read_text(encoding="utf-8"))
    comparison = compare_runs(previous, current)
    print(format_comparison(comparison))
    return 0


def dataset_preflight(pdfs: list[Path], readiness_path: Path | None = None) -> bool:
    """Stop before paid calls when answer keys or the vision server are absent."""
    sources = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
    by_id = {item["doc_id"]: item for item in sources}
    issues = []
    if len(by_id) != len(sources):
        issues.append("Duplicate document IDs in data/sources.json.")
    missing_truth = []
    scanned = []
    for pdf in pdfs:
        doc_id = pdf.stem
        record = by_id.get(doc_id)
        if not record or not record.get("source_url", "").startswith("https://"):
            issues.append(f"{doc_id}: missing public HTTPS source URL.")
        truth_path = TRUTH_DIR / f"{doc_id}.json"
        if not truth_path.exists():
            missing_truth.append(doc_id)
        elif record:
            try:
                with pymupdf.open(pdf) as opened:
                    page_count = len(opened)
                truth = load_truth(truth_path, doc_id, page_count)
                if truth["source_url"] != record["source_url"]:
                    issues.append(f"{doc_id}: answer-key source URL differs from data/sources.json.")
            except Exception as exc:
                issues.append(f"{doc_id}: invalid human answer key ({exc}).")
        if not has_usable_text(pdf):
            scanned.append(doc_id)
    if missing_truth:
        issues.append("Human answer keys missing for: " + ", ".join(missing_truth) + ".")
    if scanned:
        blocker = vision_readiness()
        if blocker:
            issues.append("Vision blocked: " + blocker + ".")
        for doc_id in scanned:
            render_pages(PDF_DIR / f"{doc_id}.pdf", RESULT_DIR / "rendered" / doc_id)
    lines = [
        "# Evaluation readiness", "",
        f"PDFs: {len(pdfs)}", f"Image-only PDFs: {len(scanned)}", "",
    ]
    lines.extend(f"- {issue}" for issue in issues)
    if not issues:
        lines.append("Dataset and vision backend are ready." if scanned else "Dataset is ready.")
    readiness_path = readiness_path or RESULT_DIR / "phase2_readiness.md"
    readiness_path.parent.mkdir(parents=True, exist_ok=True)
    readiness_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for issue in issues:
        print(issue, file=sys.stderr)
    return not issues


def run_phase1() -> int:
    """Rerun the original five text PDFs without vision or the value judge."""
    pdfs = [PDF_DIR / f"{doc_id}.pdf" for doc_id in GOLDEN_IDS]
    phase_dir = RESULT_DIR / "phase1"
    if not dataset_preflight(pdfs, phase_dir / "readiness.md"):
        print("Read results/phase1/readiness.md for the blocked steps.", file=sys.stderr)
        return 2
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("Set DEEPSEEK_API_KEY in .env before running Phase 1.", file=sys.stderr)
        return 2
    documents = []
    for pdf in pdfs:
        doc_id = pdf.stem
        print(f"Evaluating Phase 1 {doc_id}...", flush=True)
        try:
            pages = read_pdf_pages(pdf)
            truth = load_truth(TRUTH_DIR / f"{doc_id}.json", doc_id, len(pages))
            extracted = extract_facts(
                doc_id, pages, [field["field"] for field in truth["fields"]],
                phase_dir / "extracted",
            )
            documents.append(score_document(extracted, truth, pages))
        except Exception as exc:
            print(f"  failed: {exc}", file=sys.stderr)
            documents.append({"doc_id": doc_id, "status": "failed", "error": str(exc)})
    run = {
        "phase": "phase1",
        "run_at_utc": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        "documents": documents,
        "aggregate": aggregate(documents),
    }
    report = make_report(run)
    phase_dir.mkdir(parents=True, exist_ok=True)
    (phase_dir / "scores.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    (phase_dir / "report.md").write_text(report, encoding="utf-8")
    snapshot = phase_dir / "runs" / run_id(run)
    snapshot.mkdir(parents=True, exist_ok=True)
    (snapshot / "scores.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    (snapshot / "report.md").write_text(report, encoding="utf-8")
    print(report)
    return 0 if run["aggregate"]["documents_ok"] == len(pdfs) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--calibrate", action="store_true", help="Calibrate the judge on the five golden PDFs")
    mode.add_argument("--compare", metavar="RUN_ID", help="Compare the latest run with a saved run")
    mode.add_argument("--phase1", action="store_true", help="Rerun the original five text PDFs without vision or the judge")
    parser.add_argument("--reuse-ocr", action="store_true", help="Reuse Qwen transcriptions when PDF, model, and OCR prompt are unchanged")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    if args.phase1:
        return run_phase1()
    if args.compare:
        return show_comparison(args.compare)
    if args.calibrate:
        return calibrate()
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if len(pdfs) < 5:
        print(f"Expected at least five PDFs in {PDF_DIR}; found {len(pdfs)}", file=sys.stderr)
        return 2
    if not dataset_preflight(pdfs):
        print("Read results/phase2_readiness.md for the blocked steps.", file=sys.stderr)
        return 2
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("Set DEEPSEEK_API_KEY in .env before running the evaluation.", file=sys.stderr)
        return 2
    calibration = load_calibration()
    if calibration is None:
        print("Judge calibration is missing or stale; run python run_eval.py --calibrate first.", file=sys.stderr)
        return 2

    documents = []
    for pdf in pdfs:
        doc_id = pdf.stem
        print(f"Evaluating {doc_id}...", flush=True)
        try:
            vision = None
            if has_usable_text(pdf):
                pages = read_pdf_pages(pdf)
            else:
                vision = read_scanned_pdf_pages(
                    pdf, RESULT_DIR / "rendered" / doc_id, RESULT_DIR / "ocr",
                    reuse_cache=args.reuse_ocr,
                )
                pages = vision["pages"]
            truth_path = TRUTH_DIR / f"{doc_id}.json"
            if not truth_path.exists():
                raise FileNotFoundError(f"Missing human ground truth: {truth_path.name}")
            truth = load_truth(truth_path, doc_id, len(pages))
            extracted = extract_facts(
                doc_id, pages, [field["field"] for field in truth["fields"]], RESULT_DIR / "extracted"
            )
            scored = score_document(extracted, truth, pages)
            judged = judge_document(extracted, truth, pages)
            for exact, verdict in zip(scored["field_scores"], judged["verdicts"], strict=True):
                exact["judge_match"] = verdict["match"]
                exact["judge_reason"] = verdict["reason"]
            scored["judge_correct"] = sum(item["match"] for item in judged["verdicts"])
            scored["judge_accuracy"] = round(scored["judge_correct"] / scored["fields"] * 100, 2)
            scored["extraction_cost_usd_estimate"] = scored["cost_usd_estimate"]
            scored["judge_cost_usd_estimate"] = judged["cost_usd_estimate"]
            scored["cost_usd_estimate"] = round(
                scored["cost_usd_estimate"] + judged["cost_usd_estimate"], 8
            )
            scored["extraction_latency_seconds"] = scored["latency_seconds"]
            scored["judge_latency_seconds"] = judged["latency_seconds"]
            scored["vision_latency_seconds"] = vision["latency_seconds"] if vision else 0
            scored["latency_seconds"] = round(
                scored["latency_seconds"] + judged["latency_seconds"]
                + scored["vision_latency_seconds"], 3
            )
            scored["judge_usage"] = judged["usage"]
            if vision:
                scored["vision_model"] = vision["model"]
                scored["vision_usage"] = vision["usage"]
                scored["vision_cached"] = vision["cache_hit"]
            documents.append(scored)
        except Exception as exc:
            print(f"  failed: {exc}", file=sys.stderr)
            documents.append({"doc_id": doc_id, "status": "failed", "error": str(exc)})

    results = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        "documents": documents, "aggregate": aggregate(documents),
    }
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    previous_path = RESULT_DIR / "scores.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else None
    if previous is not None:
        old_report_path = RESULT_DIR / "report.md"
        old_report = old_report_path.read_text(encoding="utf-8") if old_report_path.exists() else make_report(previous)
        save_run_snapshot(previous, old_report)
    comparison = compare_runs(previous, results) if previous is not None else None
    (RESULT_DIR / "scores.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    report = make_report(results, comparison)
    (RESULT_DIR / "report.md").write_text(report, encoding="utf-8")
    save_run_snapshot(results, report)
    if results["aggregate"]["documents_ok"] == len(pdfs):
        readme_path = ROOT / "README.md"
        readme = readme_path.read_text(encoding="utf-8")
        start, end = "<!-- RESULTS_START -->", "<!-- RESULTS_END -->"
        if readme.count(start) != 1 or readme.count(end) != 1:
            raise ValueError("README results markers are missing or duplicated")
        before, rest = readme.split(start, 1)
        _, after = rest.split(end, 1)
        readme_path.write_text(
            before + start + "\n\n" + report + "\n" + end + after,
            encoding="utf-8",
        )
    print(report)
    return 0 if results["aggregate"]["documents_ok"] == len(pdfs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
