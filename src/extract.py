"""Read text PDFs and extract requested facts with one DeepSeek call."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pymupdf
from openai import OpenAI

MODEL = "deepseek-flash"
BASE_URL = "https://api.deepseek.com"
PUBLIC_MODEL_LABEL = "deepseek-flash"


def read_pdf_pages(path: Path) -> list[str]:
    with pymupdf.open(path) as pdf:
        pages = [page.get_text(sort=True).strip() for page in pdf]
    if not pages or sum(len(page) for page in pages) < 100:
        raise ValueError(f"No usable text layer in {path.name}; OCR is out of scope")
    return pages


def extract_facts(
    doc_id: str, pages: list[str], field_names: list[str], output_dir: Path
) -> dict:
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key or key == "your_key_here":
        raise RuntimeError("DEEPSEEK_API_KEY is missing; set it in .env")

    page_text = "\n\n".join(
        f"--- PAGE {number} ---\n{text}" for number, text in enumerate(pages, 1)
    )
    system = (
        "Extract facts only from the supplied document text. Return one JSON object with "
        'a "fields" array. Each item must have "field", "value", and "source_page". '
        "Use null for a missing value or source_page. Do not infer or guess. "
        "Preserve names and IDs as printed, including any name suffix such as Jr., Sr., or III; "
        "write dates as YYYY-MM-DD and amounts as numbers. "
        'Example JSON: {"fields":[{"field":"invoice_number","value":"A-1",'
        '"source_page":1}]}.'
    )
    user = (
        f"Document ID: {doc_id}\n"
        f"Extract exactly these field names: {json.dumps(field_names)}\n"
        "For financial tables, use the latest period shown and do not mix quarter and year-to-date values.\n\n"
        f"DOCUMENT TEXT:\n{page_text}"
    )
    model = os.getenv("DEEPSEEK_MODEL", MODEL)
    base_url = os.getenv("DEEPSEEK_BASE_URL", BASE_URL)
    client = OpenAI(
        api_key=key,
        base_url=base_url,
        timeout=120.0,
    )
    started = time.perf_counter()
    request = dict(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0,
        response_format={"type": "json_object"},
        max_tokens=1200,
    )
    if base_url.rstrip("/") == BASE_URL:
        request["extra_body"] = {"thinking": {"type": "disabled"}}
    response = client.chat.completions.create(**request)
    latency = time.perf_counter() - started
    raw = response.choices[0].message.content or ""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{doc_id}.txt").write_text(raw, encoding="utf-8")
    try:
        parsed = json.loads(raw)
        fields = parsed["fields"]
        if not isinstance(fields, list) or len(fields) != len(field_names):
            raise ValueError("Wrong number of fields")
        if [item.get("field") for item in fields] != field_names:
            raise ValueError("Fields differ from the requested order or names")
        for item in fields:
            if set(item) != {"field", "value", "source_page"}:
                raise ValueError(f"Invalid field shape: {item!r}")
            if item["value"] is not None and not isinstance(item["value"], (str, int, float)):
                raise ValueError(f"Invalid value type: {item!r}")
            page = item["source_page"]
            if page is not None and (not isinstance(page, int) or not 1 <= page <= len(pages)):
                raise ValueError(f"Invalid source_page: {item!r}")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid JSON extraction for {doc_id}: {exc}") from exc

    usage = response.usage
    if usage is None:
        raise ValueError(f"DeepSeek did not return token usage for {doc_id}")
    result = {
        "doc_id": doc_id,
        "model": PUBLIC_MODEL_LABEL,
        "fields": fields,
        "usage": {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "prompt_cache_hit_tokens": getattr(usage, "prompt_cache_hit_tokens", 0),
            "prompt_cache_miss_tokens": getattr(usage, "prompt_cache_miss_tokens", None),
        },
        "latency_seconds": round(latency, 3),
        "api_created_at": response.created,
    }
    (output_dir / f"{doc_id}.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result
