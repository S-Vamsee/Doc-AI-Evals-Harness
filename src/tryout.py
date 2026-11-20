"""Try any text PDF with no answer key and write a trace a person can read."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

import pymupdf

from src import core_pipeline
from src.core_pipeline import LOCAL_TRYOUT_SOURCE, run_text_page


ROOT = Path(__file__).resolve().parents[1]
TRYOUT_ROOT = ROOT / "results" / "tryouts"
REGISTRY_PATH = ROOT / "data" / "tryout_registry.json"
MIN_PAGE_TEXT = 40
_FIELD_NAME = re.compile(r"[a-z][a-z0-9_]*")


class TryoutRefused(ValueError):
    """The document cannot be processed, for a reason the person can act on."""


def parse_fields(raw: str | None) -> list[str] | None:
    """Turn ``total,due_date`` into a checked list of field names."""
    if raw is None:
        return None
    fields = [item.strip() for item in raw.split(",") if item.strip()]
    if not fields:
        raise TryoutRefused("--fields needs at least one field name")
    invalid = [item for item in fields if not _FIELD_NAME.fullmatch(item)]
    if invalid:
        raise TryoutRefused("Field names use lowercase letters, digits and underscores: "
                            + ", ".join(invalid))
    if len(set(fields)) != len(fields):
        raise TryoutRefused("Each field name can be requested once")
    return fields


def inspect_pdf(pdf_path: Path) -> tuple[bytes, list[dict]]:
    """Classify every page before any model call, refusing unreadable files."""
    path = Path(pdf_path)
    if not path.is_file():
        raise TryoutRefused(f"File not found: {path}")
    data = path.read_bytes()
    if not data.startswith(b"%PDF"):
        raise TryoutRefused(f"Not a PDF file: {path.name}")
    try:
        document = pymupdf.open(path)
    except Exception as exc:
        raise TryoutRefused(f"This PDF cannot be opened: {path.name} ({type(exc).__name__})") from exc
    with document:
        if document.needs_pass:
            raise TryoutRefused(f"This PDF is password-protected: {path.name}")
        if len(document) == 0:
            raise TryoutRefused(f"This PDF has no pages: {path.name}")
        pages = []
        for number, page in enumerate(document, 1):
            has_text = len(page.get_text(sort=True).strip()) >= MIN_PAGE_TEXT
            kind = "text" if has_text else "scan" if page.get_images() else "empty"
            pages.append({"page": number, "kind": kind})
    if all(item["kind"] == "scan" for item in pages):
        raise TryoutRefused("This PDF is scanned. Checking scanned pages arrives on Day 6, "
                            "so it cannot be tried yet.")
    return data, pages


def record_tryout(sha256: str, page_count: int, registry_path: Path = REGISTRY_PATH) -> None:
    """Remember a seen document by fingerprint only, so it can never be held back."""
    path = Path(registry_path)
    registry = (json.loads(path.read_text(encoding="utf-8")) if path.is_file()
                else {"purpose": "Documents already tried; never eligible for the held-back set.",
                      "documents": {}})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = registry["documents"].setdefault(sha256, {"first_tried": now, "pages": page_count,
                                                      "tries": 0})
    entry["tries"] += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fence(text: str, info: str = "text") -> str:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    marks = "`" * max(3, longest + 1)
    return f"{marks}{info}\n{text}\n{marks}"


def _cell(value: object) -> str:
    text = "—" if value is None or value == "" else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _write_trace(work: Path, name: str, page: int, calls: list[dict]) -> dict:
    """Explain one page from top to bottom using only what the run saved."""
    result = json.loads((work / "result.json").read_text(encoding="utf-8"))
    text_path = work / "page_text.txt"
    text = text_path.read_text(encoding="utf-8").rstrip("\n") if text_path.is_file() else ""
    (work / "requests.json").write_text(json.dumps(calls, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
    status = "complete" if result.get("complete") else "incomplete"
    lines = [f"# Trace: {name}, page {page}", "",
             f"Status: {status}. Extracted, unscored: no answer key was used, so this "
             "trace reports what could be confirmed on the page and gives no accuracy figure.", "",
             "## 1. What was read", "", _fence(text or "(no text was read)"), "",
             "## 2. What the model was asked", ""]
    for number, call in enumerate(calls, 1):
        lines.extend([f"### Request {number}: {call['purpose']}", ""])
        for message in call["messages"]:
            content = message["content"].replace(text, "[the page text from section 1]") if text \
                else message["content"]
            lines.extend([f"{message['role'].capitalize()} message:", "", _fence(content), ""])
    if not calls:
        lines.extend(["No request was sent.", ""])
    records = result.get("records", [])
    lines.extend(["## 3. What the model returned", ""])
    if records:
        lines.extend(["| ID | Request | Kind | Field | Value | Read or inferred | Quote |",
                      "| --- | --- | --- | --- | --- | --- | --- |"])
        lines.extend("| " + " | ".join(_cell(item) for item in (
            fact["fact_id"], fact["source_call"], fact["kind"], fact["relation"],
            fact["value"], fact["origin"], fact["evidence"]["quote"])) + " |" for fact in records)
    else:
        lines.append("No facts were returned.")
    lines.extend(["", "## 4. What each check decided", ""])
    if records:
        lines.extend(["| ID | State | Quote backs the value | Found at | Why |",
                      "| --- | --- | --- | --- | --- |"])
        lines.extend("| " + " | ".join(_cell(item) for item in (
            fact["fact_id"], fact["state"], fact.get("evidence_support"),
            fact["evidence"]["bbox"], fact["reason"])) + " |" for fact in records)
    else:
        lines.append("Nothing was checked.")
    lines.extend(["", "## 5. Final counts", ""])
    counts = result.get("counts")
    if counts:
        lines.extend([f"- Facts: {counts['facts_in']}", f"- Verified: {counts['verified']}",
                      f"- Uncertain: {counts['uncertain']}", f"- Failed: {counts['failed']}",
                      f"- Not present on the page: {counts['skipped']}"])
    else:
        lines.append("No counts were produced because the run stopped early.")
    failures = result.get("failures", [])
    lines.extend(["", "Failures:" if failures else "No stage failures were recorded."])
    lines.extend(f"- {item['stage']}: {item['reason']}" for item in failures)
    cost = result.get("reference_cost_usd_estimate")
    lines.extend(["", "## 6. Time and estimated cost", "",
                  f"- Model time: {result.get('latency_seconds', 0.0):.1f} seconds",
                  "- Estimated model cost: " +
                  (f"${cost:.6f} at reference token rates, not a billing record"
                   if cost is not None else "not available"),
                  *([f"- Provider-reported cost: ${result['provider_cost_usd']:.6f}"]
                    if result.get("provider_cost_usd") is not None else []),
                  "", "## 7. Saved files", "",
                  "`requests.json`, `keyed.raw.json` and `open.raw.json` (when requested), "
                  "`result.json`, `review.json`, `manifest.json`, `report.md`."])
    (work / "trace.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def run_tryout(pdf_path: Path, fields: list[str] | None = None, *,
               output_root: Path | None = None, registry_path: Path = REGISTRY_PATH,
               model_request=None) -> Path:
    """Process every text page and return the folder holding ``summary.md``."""
    path = Path(pdf_path)
    data, pages = inspect_pdf(path)
    sha256 = hashlib.sha256(data).hexdigest()
    record_tryout(sha256, len(pages), registry_path)
    safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", path.stem)[:60] or "document"
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = Path(output_root or TRYOUT_ROOT) / f"{safe_name}_{sha256[:8]}" / run_id
    folder.mkdir(parents=True, exist_ok=False)
    rows = []
    for item in pages:
        number, kind = item["page"], item["kind"]
        if kind != "text":
            note = ("scanned page, not checked until Day 6" if kind == "scan"
                    else "empty page, nothing to read")
            rows.append({"page": number, "status": "skipped" if kind == "scan" else "empty",
                         "note": note, "counts": None, "cost": 0.0, "trace": None})
            continue
        calls: list[dict] = []

        def recorder(messages: list[dict]) -> dict:
            keyed = bool(fields) and not calls
            calls.append({"purpose": "your named fields" if keyed else "other facts on the page",
                          "messages": messages})
            return (model_request or core_pipeline._live_request)(messages)

        work = run_text_page(f"tryout_{sha256[:12]}", path, number,
                             f"{LOCAL_TRYOUT_SOURCE}{sha256[:12]}", document_type="tryout",
                             output_root=folder / f"page-{number:03d}", model_request=recorder,
                             requested_fields=fields)
        result = _write_trace(work, path.name, number, calls)
        rows.append({"page": number, "status": "complete" if result.get("complete") else "incomplete",
                     "note": "; ".join(failure["reason"] for failure in result.get("failures", [])),
                     "counts": result.get("counts"),
                     "cost": result.get("reference_cost_usd_estimate") or 0.0,
                     "trace": (work / "trace.md").relative_to(folder).as_posix()})
    complete = all(row["status"] in {"complete", "empty"} for row in rows)
    summary = {"file": path.name, "sha256": sha256, "complete": complete,
               "exit_code": int(not complete), "label": "extracted, unscored", "fields": fields,
               "pages": rows, "estimated_cost_usd": sum(row["cost"] for row in rows)}
    (folder / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    lines = [f"# Tryout: {path.name}", "",
             "Extracted, unscored. No answer key was used, so no accuracy figure is given.", "",
             f"Status: {'complete' if complete else 'incomplete'}.", "",
             "| Page | Status | Facts | Verified | Uncertain | Failed | Not present | Trace | Note |",
             "| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |"]
    for row in rows:
        counts = row["counts"] or {}
        lines.append("| " + " | ".join(_cell(value) for value in (
            row["page"], row["status"], counts.get("facts_in"), counts.get("verified"),
            counts.get("uncertain"), counts.get("failed"), counts.get("skipped"),
            row["trace"], row["note"])) + " |")
    lines.extend(["", f"Estimated model cost: ${summary['estimated_cost_usd']:.6f} at reference "
                      "token rates, not a billing record."])
    (folder / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return folder
