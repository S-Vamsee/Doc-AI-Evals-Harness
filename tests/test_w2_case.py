"""The public W-2 sample exposes a text-layer evidence gap."""

from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]


def test_printed_tax_year_is_not_a_standalone_text_word():
    with pymupdf.open(ROOT / "data" / "pdfs" / "w2_001.pdf") as pdf:
        words = [item[4] for item in pdf[0].get_text("words")]
    assert "2026" not in words
    assert any("2026" in word for word in words)
