"""Independent, positioned Tesseract reading of a rendered PDF page."""

from __future__ import annotations

import os
from pathlib import Path

import pymupdf


def read_tesseract_words(page: pymupdf.Page, *, dpi: int = 150,
                         tessdata: str | None = None) -> list[dict]:
    if dpi < 72:
        raise ValueError("OCR resolution must be at least 72 DPI")
    if tessdata is None:
        tessdata = os.getenv("TESSDATA_PREFIX")
    if tessdata is None:
        default = Path(r"C:\Program Files\Tesseract-OCR\tessdata")
        tessdata = str(default) if default.is_dir() else None
    options = {"language": "eng", "dpi": dpi, "full": True}
    if tessdata:
        options["tessdata"] = tessdata
    ocr_page = page.get_textpage_ocr(**options)
    return [{"page": page.number + 1, "text": item[4],
             "bbox": [float(item[0]), float(item[1]), float(item[2]), float(item[3])],
             "source": "tesseract"}
            for item in page.get_text("words", textpage=ocr_page)
            if str(item[4]).strip()]
