"""Build a blind, source-backed judge calibration sheet from public PDFs.

The proposed groups exist only in this design. Neither the owner sheet nor the
pending pair file contains a proposed answer or a judge verdict.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
import random
import re
import unicodedata

import pymupdf

from src.scan_evidence import read_tesseract_words


@dataclass(frozen=True)
class Case:
    group: str
    doc_id: str
    field: str
    candidate: object | None  # None means repeat the human reference exactly.
    source_quotes: tuple[tuple[int | None, str], ...]


def C(group: str, doc_id: str, field: str, candidate: object | None,
      quote: str | tuple[tuple[int, str], ...]) -> Case:
    sources = ((None, quote),) if isinstance(quote, str) else quote
    return Case(group, doc_id, field, candidate, sources)


CASES = (
    # Twelve exact repeats. Other groups contain real variations and confusions.
    C("identical", "invoice_001", "invoice_number", None, "INV-2026-0142"),
    C("identical", "invoice_002", "customer_name", None, "Riverside High School"),
    C("identical", "receipt_002", "order_number", None, "#NV-10482"),
    C("identical", "scan_report_001", "days_open", None, "302"),
    C("identical", "statement_001", "account_holder", None, "Sam Specimen"),
    C("identical", "utility_001", "provider_name", None, "Brightside Energy"),
    C("identical", "filing_001", "net_income_2024_thousands", None, "6,561"),
    C("identical", "form_library_001", "organization_name", None,
      "Larkfield Community Library"),
    C("identical", "scan_letter_001", "reference_number", None, "BHS/MC/2026/118"),
    C("identical", "contract_offer_001", "hourly_rate", None, "28.00 USD"),
    C("identical", "scan_notice_001", "block_a_water_off_start", None, "09:00"),
    C("identical", "w2_001", "wages", None, "80,000.00"),

    # Sixteen equivalent forms: dates, currency, case, punctuation, abbreviation.
    C("equivalent", "invoice_001", "invoice_date", "18 September 2026",
      "18 September 2026"),
    C("equivalent", "invoice_001", "total_amount", "₹17,348.36", "17,348.36"),
    C("equivalent", "invoice_002", "total_amount", "$329.40", "$329.40"),
    C("equivalent", "invoice_003", "total_amount", "325.41 CAD", "325.41 CAD"),
    C("equivalent", "utility_001", "total_due", "$53.78", "$53.78"),
    C("equivalent", "receipt_002", "total_amount", "$7.75", "$7.75"),
    C("equivalent", "filing_001", "company_name", "Mama's Creations, Inc",
      "MAMA'S CREATIONS, INC."),
    C("equivalent", "receipt_001", "merchant_name", "Corner Cafe", "CORNER CAFE"),
    C("equivalent", "scan_report_001", "annual_visits", "41,280", "41,280"),
    C("equivalent", "scan_report_001", "printed_book_loans", "58,914", "58,914"),
    C("equivalent", "statement_001", "opening_balance", "₹48,230.55", "48,230.55"),
    C("equivalent", "statement_001", "period_start_date", "01/08/2026", "01/08/2026"),
    C("equivalent", "scan_invoice_001", "invoice_date", "2026-09-18",
      "18 September 2026"),
    C("equivalent", "notice_001", "notice_date", "6 October 2026", "6/10/2026"),
    C("equivalent", "form_001", "application_due_date", "February 18, 2025",
      "February 18, 2025"),
    C("equivalent", "invoice_002", "vendor_name", "Meridian Supply Company",
      "Meridian Supply Co."),

    # Twenty-two plausible errors. The conflicting values or the underlying
    # ambiguous print all occur in the named public PDF.
    C("plausible_wrong", "filing_001", "gross_profit_2024_thousands", "19,418", "19,418"),
    C("plausible_wrong", "filing_001", "net_income_2024_thousands", "2,304", "2,304"),
    C("plausible_wrong", "scan_report_001", "annual_visits", "58,914", "58,914"),
    C("plausible_wrong", "notice_001", "end_time", "14:00", "14:00"),
    C("plausible_wrong", "statement_001", "opening_balance", "₹46,736.38", "46,736.38"),
    C("plausible_wrong", "receipt_001", "total_amount", "180.00", "180.00"),
    C("plausible_wrong", "utility_001", "total_due", "$37.63", "$37.63"),
    C("plausible_wrong", "invoice_001", "total_amount", "₹14,702.00", "14,702.00"),
    C("plausible_wrong", "invoice_002", "total_amount", "$305.00", "$305.00"),
    C("plausible_wrong", "invoice_003", "total_amount", "309.92 CAD", "309.92 CAD"),
    C("plausible_wrong", "contract_offer_001", "hourly_rate", "1,176.00 USD",
      "1,176.00 USD"),
    C("plausible_wrong", "contract_amendment_001", "new_expense_cap", "250.00 USD",
      "250.00 USD"),
    C("plausible_wrong", "invoice_001", "vendor_name", "Example Traders (fictional)",
      "Example Traders (fictional)"),
    C("plausible_wrong", "invoice_002", "vendor_name", "Riverside High School",
      "Riverside High School"),
    C("plausible_wrong", "invoice_003", "supplier_name_with_id",
      "Harbour Kitchen Group (BUY-GRP)", "Harbour Kitchen Group (BUY-GRP)"),
    C("plausible_wrong", "contract_offer_001", "employer_name",
      "Team member 5 (EMP-05)", "Team member 5 (EMP-05)"),
    C("plausible_wrong", "statement_001", "account_holder", "Alex Example", "Alex Example"),
    C("plausible_wrong", "statement_001", "period_start_date", "2026-01-08",
      "01/08/2026"),
    C("plausible_wrong", "receipt_002", "purchase_date", "2026-06-01", "2026-01-06"),
    C("plausible_wrong", "w2_001", "federal_income_tax_withheld", "9,600.00",
      "9,600.00"),
    C("plausible_wrong", "form_handwritten_001", "symptoms", "mild headache",
      "mild headache, SAMPLE only"),
    C("plausible_wrong", "scan_agreement_001", "monthly_licence_fee", "55,000",
      "55,000"),

    # Ten borderline cases are deliberately left to the owner to rule on.
    C("borderline", "receipt_002", "order_number", "NV-10482", "#NV-10482"),
    C("borderline", "invoice_003", "supplier_name_with_id", "Harbour Food Supply",
      "Harbour Food Supply (SUP-02)"),
    C("borderline", "contract_offer_001", "candidate_name_with_id", "Team member 5",
      "Team member 5 (EMP-05)"),
    C("borderline", "form_001", "applicant_name", "Jane Jacobs, Planner III",
      ((1, "Jane Jacobs"), (2, "Planner III"))),
    C("borderline", "filing_001", "company_name", "Mama's Creations",
      "MAMA'S CREATIONS, INC."),
    C("borderline", "w2_001", "employee_name", "Alex Q Sample",
      "Alex Q Sample Jr."),
    C("borderline", "scan_notice_001", "block_a_water_off_date", "2026-10-12",
      "Mon 12 Oct"),
    C("borderline", "scan_notice_001", "block_a_water_off_date", "Monday 12 October",
      "Mon 12 Oct"),
    C("borderline", "utility_001", "account_number", "SAMPLE-7788",
      "ACC-SAMPLE-7788"),
    C("borderline", "invoice_002", "vendor_name", "Meridian Supply",
      "Meridian Supply Co."),
)


def _field_map(root: Path) -> dict[tuple[str, str], tuple[dict, dict]]:
    result = {}
    for path in (root / "data" / "ground_truth").glob("*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for field in doc["fields"]:
            result[(doc["doc_id"], field["field"])] = (doc, field)
    return result


def build_sheet(root: Path) -> dict:
    fields = _field_map(root)
    rng = random.Random(20261114)
    cases = list(CASES)
    rng.shuffle(cases)
    numbers = rng.sample(range(100000, 999999), len(cases))
    pairs = []
    for case, number in zip(cases, numbers, strict=True):
        doc, field = fields[(case.doc_id, case.field)]
        if field["value"] is None:
            raise ValueError(f"Calibration reference is null: {case.doc_id}.{case.field}")
        if not doc["source_url"].startswith("https://"):
            raise ValueError(f"Missing public source URL for {case.doc_id}")
        candidate = field["value"] if case.candidate is None else case.candidate
        sources = [{"page": page or field["page"], "quote": quote}
                   for page, quote in case.source_quotes]
        pairs.append({
            "pair_id": f"P-{number:06d}", "doc_id": case.doc_id,
            "source_url": doc["source_url"], "field": case.field,
            "value_type": field["type"], "reference": field["value"],
            "candidate": candidate, "reference_page": field["page"],
            "source_quotes": sources, "human_label": None,
        })
    return {"status": "pending_human_labels", "pairs": pairs}


def _words(value: str) -> list[str]:
    return re.findall(r"\w+", unicodedata.normalize("NFKC", value).casefold())


def _contains_tokens(page_text: str, quote: str) -> bool:
    words, wanted = _words(page_text), _words(quote)
    return bool(wanted) and any(words[start:start + len(wanted)] == wanted
                                for start in range(len(words) - len(wanted) + 1))


def verify_public_pdf_quotes(root: Path, pairs: list[dict]) -> None:
    """Read only named public PDFs and check every cited quote on its page."""
    cache = {}
    for pair in pairs:
        path = root / "data" / "pdfs" / (pair["doc_id"] + ".pdf")
        if not path.is_file():
            raise ValueError(f"Missing public PDF: {path.name}")
        for source in pair["source_quotes"]:
            key = (pair["doc_id"], source["page"])
            if key not in cache:
                with pymupdf.open(path) as pdf:
                    page = pdf[source["page"] - 1]
                    text = page.get_text("text")
                    if len(text.strip()) < 50:
                        text = " ".join(word["text"] for word in read_tesseract_words(page))
                    cache[key] = text
            if not _contains_tokens(cache[key], source["quote"]):
                raise ValueError(f"Source quote missing: {pair['doc_id']} p{source['page']} "
                                 f"{source['quote']!r}")


def write_sheet(root: Path, *, verify_sources: bool = True) -> tuple[Path, Path]:
    directory = root / "data" / "calibration"
    directory.mkdir(parents=True, exist_ok=True)
    review_path = directory / "owner_review.csv"
    labels_path = directory / "owner_labels.csv"
    for owner_path in (review_path, labels_path):
        if owner_path.exists():
            with owner_path.open(newline="", encoding="utf-8-sig") as stream:
                previous = list(csv.DictReader(stream))
            if any(row.get("human_label_true_or_false", "").strip() for row in previous):
                raise ValueError(f"Owner review {owner_path.name} contains labels; refusing to overwrite")
    sheet = build_sheet(root)
    if verify_sources:
        verify_public_pdf_quotes(root, sheet["pairs"])
    pending_path = directory / "pairs.pending.json"
    pending_path.write_text(json.dumps(sheet, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    with review_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["pair_id", "doc_id", "field", "value_type", "reference",
                         "candidate", "reference_page", "source_excerpt", "source_url",
                         "human_label_true_or_false"])
        for pair in sheet["pairs"]:
            excerpts = " | ".join(f"p{source['page']}: {source['quote']}"
                                  for source in pair["source_quotes"])
            writer.writerow([pair["pair_id"], pair["doc_id"], pair["field"],
                             pair["value_type"], pair["reference"], pair["candidate"],
                             pair["reference_page"], excerpts, pair["source_url"], ""])
    with labels_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["pair_id", "human_label_true_or_false"])
        writer.writerows((pair["pair_id"], "") for pair in sheet["pairs"])
    return pending_path, review_path


if __name__ == "__main__":
    repo = Path(__file__).resolve().parents[1]
    pending, review = write_sheet(repo)
    print(f"Wrote {pending} and {review}")
