"""Read image-only PDFs with a local Qwen vision model served by Ollama."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pymupdf

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3-vl:2b-instruct"
OCR_PROMPT = (
    "Transcribe every visible word and number on this document page in reading order. "
    "Keep headings, field labels, dates, currency amounts, and table rows. "
    "Do not infer missing text or add commentary."
)


def vision_config() -> tuple[str, str]:
    base_url = os.getenv("QWEN_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = os.getenv("QWEN_MODEL", DEFAULT_MODEL).strip()
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("QWEN_BASE_URL must point to a local HTTP Ollama server")
    if not model:
        raise ValueError("QWEN_MODEL is empty")
    return base_url, model


def _json_request(url: str, payload: dict | None = None, timeout: int = 10) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"Cannot reach local Ollama at {url}: {exc}") from exc


def vision_readiness() -> str | None:
    """Return a user-facing blocker, or None when the selected model is installed."""
    try:
        base_url, model = vision_config()
        response = _json_request(f"{base_url}/api/tags")
    except (ValueError, RuntimeError) as exc:
        return str(exc)
    installed = {item.get("name") for item in response.get("models", [])}
    if model not in installed:
        return f"Qwen model {model} is not installed; run: ollama pull {model}"
    return None


def vision_cache_signature(path: Path) -> str:
    """Pin a saved transcription to the PDF, model digest, and OCR prompt."""
    base_url, model = vision_config()
    response = _json_request(f"{base_url}/api/tags")
    selected = next((item for item in response.get("models", []) if item.get("name") == model), None)
    if selected is None:
        raise RuntimeError(f"Qwen model {model} is not installed")
    digest = selected.get("digest", "")
    data = b"\0".join((
        path.read_bytes(), model.encode(), digest.encode(), OCR_PROMPT.encode(), b"150dpi"
    ))
    return hashlib.sha256(data).hexdigest()


def has_usable_text(path: Path, minimum_characters: int = 100) -> bool:
    with pymupdf.open(path) as pdf:
        return sum(len(page.get_text().strip()) for page in pdf) >= minimum_characters


def render_pages(path: Path, output_dir: Path) -> list[Path]:
    """Render pages at 150 DPI for local vision reading."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    with pymupdf.open(path) as pdf:
        for number, page in enumerate(pdf, 1):
            target = output_dir / f"page_{number:03d}.png"
            page.get_pixmap(matrix=pymupdf.Matrix(150 / 72, 150 / 72), alpha=False).save(target)
            paths.append(target)
    return paths


def read_scanned_pdf_pages(
    path: Path, rendered_dir: Path, ocr_dir: Path, reuse_cache: bool = False
) -> dict:
    """Transcribe each page through local Ollama and retain per-page text."""
    blocker = vision_readiness()
    if blocker:
        raise RuntimeError(blocker)
    base_url, model = vision_config()
    signature = vision_cache_signature(path)
    cached_path = ocr_dir / f"{path.stem}.json"
    if reuse_cache and cached_path.exists():
        saved = json.loads(cached_path.read_text(encoding="utf-8"))
        if saved.get("cache_signature") == signature and saved.get("pages"):
            print("  Reusing Qwen transcription for unchanged PDF and model.", flush=True)
            return {**saved, "latency_seconds": 0.0, "usage": [], "cache_hit": True}
    images = render_pages(path, rendered_dir)
    pages = []
    usage = []
    started = time.perf_counter()
    for number, image in enumerate(images, 1):
        print(f"  Qwen reading page {number}/{len(images)}...", flush=True)
        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": OCR_PROMPT,
                "images": [base64.b64encode(image.read_bytes()).decode("ascii")],
            }],
            "options": {"temperature": 0, "num_predict": 4096},
            "stream": False,
            "think": False,
        }
        response = _json_request(f"{base_url}/api/chat", payload, timeout=900)
        content = response.get("message", {}).get("content", "").strip()
        if not content:
            raise ValueError(f"Qwen returned no text for {path.name} page {number}")
        pages.append(content)
        usage.append({
            "prompt_tokens": response.get("prompt_eval_count"),
            "completion_tokens": response.get("eval_count"),
            "duration_nanoseconds": response.get("total_duration"),
        })
    result = {
        "doc_id": path.stem,
        "model": model,
        "pages": pages,
        "latency_seconds": round(time.perf_counter() - started, 3),
        "usage": usage,
        "cache_signature": signature,
        "cache_hit": False,
    }
    ocr_dir.mkdir(parents=True, exist_ok=True)
    cached_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result
