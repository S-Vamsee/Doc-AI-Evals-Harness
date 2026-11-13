"""Run the five-document CLI evaluation: python run_eval.py."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.extract import extract_facts, read_pdf_pages
from src.report import make_report
from src.score import score_document

PDF_DIR = ROOT / "data" / "pdfs"
TRUTH_DIR = ROOT / "data" / "ground_truth"
RESULT_DIR = ROOT / "results"


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
    return {
        "documents_ok": len(successful), "documents_failed": len(documents) - len(successful),
        "fields": fields, "correct": sum(doc["correct"] for doc in successful),
        "accuracy": round(sum(doc["correct"] for doc in successful) / fields * 100, 2) if fields else 0,
        "extracted_facts": facts, "grounded": sum(doc["grounded"] for doc in successful),
        "groundedness": round(sum(doc["grounded"] for doc in successful) / facts * 100, 2) if facts else None,
        "cost_usd_estimate": round(sum(doc["cost_usd_estimate"] for doc in successful), 8),
        "mean_latency_seconds": round(sum(doc["latency_seconds"] for doc in successful) / len(successful), 3) if successful else 0,
    }


def main() -> int:
    load_dotenv(ROOT / ".env")
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if len(pdfs) != 5:
        print(f"Expected five PDFs in {PDF_DIR}; found {len(pdfs)}", file=sys.stderr)
        return 2
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("Set DEEPSEEK_API_KEY in .env before running the evaluation.", file=sys.stderr)
        return 2

    documents = []
    for pdf in pdfs:
        doc_id = pdf.stem
        print(f"Evaluating {doc_id}...", flush=True)
        try:
            pages = read_pdf_pages(pdf)
            truth_path = TRUTH_DIR / f"{doc_id}.json"
            if not truth_path.exists():
                raise FileNotFoundError(f"Missing human ground truth: {truth_path.name}")
            truth = load_truth(truth_path, doc_id, len(pages))
            extracted = extract_facts(
                doc_id, pages, [field["field"] for field in truth["fields"]], RESULT_DIR / "extracted"
            )
            documents.append(score_document(extracted, truth, pages))
        except Exception as exc:
            print(f"  failed: {exc}", file=sys.stderr)
            documents.append({"doc_id": doc_id, "status": "failed", "error": str(exc)})

    results = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "documents": documents, "aggregate": aggregate(documents),
    }
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / "scores.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    report = make_report(results)
    (RESULT_DIR / "report.md").write_text(report, encoding="utf-8")
    if results["aggregate"]["documents_ok"] == 5:
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
    return 0 if results["aggregate"]["documents_ok"] == 5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
