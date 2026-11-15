"""Record one authorized live extraction pass for the offline injection test."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from types import SimpleNamespace

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src import extract  # noqa: E402


HERE = Path(__file__).resolve().parent
PDF_DIR = ROOT / "data" / "injection"
FIELDS = ["invoice_number", "vendor_name", "total_amount"]
CASES = ("baseline", "system_spoof", "delimiter_spoof", "answer_spoof")


def _hash_messages(messages: list[dict]) -> str:
    payload = json.dumps(messages, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    load_dotenv(ROOT / ".env")
    real_openai = extract.OpenAI
    cases = {}
    for name in CASES:
        pdf = PDF_DIR / f"{name}.pdf"
        page_text = extract.read_pdf_pages(pdf)
        captured = {}

        def factory(**client_options):
            real_client = real_openai(**client_options)

            def create(**request):
                captured["request_sha256"] = _hash_messages(request["messages"])
                return real_client.chat.completions.create(**request)

            return SimpleNamespace(chat=SimpleNamespace(
                completions=SimpleNamespace(create=create)))

        extract.OpenAI = factory
        try:
            work = ROOT / "results" / "experiments" / "injection_live" / name
            result = extract.extract_facts("injection_invoice", page_text, FIELDS, work)
        finally:
            extract.OpenAI = real_openai
        cases[name] = {
            "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "request_sha256": captured["request_sha256"],
            "response_text": (work / "injection_invoice.txt").read_text(encoding="utf-8"),
            "fields": result["fields"],
            "usage": result["usage"],
            "api_created_at": result["api_created_at"],
        }
        print(f"{name}: " + json.dumps(result["fields"], ensure_ascii=False), flush=True)
    record = {"recorded_at_utc": datetime.now(timezone.utc).isoformat(),
              "model_label": "deepseek-flash", "cases": cases}
    (HERE / "recordings.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
