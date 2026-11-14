"""Detect image-only PDFs and prepare page images for a configured Qwen vision server."""

from __future__ import annotations

from pathlib import Path

import pymupdf


def has_usable_text(path: Path, minimum_characters: int = 100) -> bool:
    with pymupdf.open(path) as pdf:
        return sum(len(page.get_text().strip()) for page in pdf) >= minimum_characters


def render_pages(path: Path, output_dir: Path) -> list[Path]:
    """Render pages at 150 DPI; no OCR or model call occurs here."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    with pymupdf.open(path) as pdf:
        for number, page in enumerate(pdf, 1):
            target = output_dir / f"page_{number:03d}.png"
            page.get_pixmap(matrix=pymupdf.Matrix(150 / 72, 150 / 72), alpha=False).save(target)
            paths.append(target)
    return paths
