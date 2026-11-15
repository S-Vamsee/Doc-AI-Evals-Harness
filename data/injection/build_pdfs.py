"""Create the four self-made, text-layer prompt-injection test pages."""

from pathlib import Path
import textwrap

import pymupdf


HERE = Path(__file__).resolve().parent


def build() -> None:
    for source in sorted(HERE.glob("*.txt")):
        pdf = pymupdf.open()
        page = pdf.new_page(width=595, height=842)
        y = 72
        for raw in source.read_text(encoding="utf-8").splitlines():
            if not raw:
                y += 10
                continue
            for line in textwrap.wrap(raw, width=90, break_long_words=False):
                page.insert_text((72, y), line, fontsize=9, fontname="helv")
                y += 15
        if y > 790:
            raise ValueError(f"Text does not fit one page: {source.name}")
        output = source.with_suffix(".pdf")
        pdf.save(output, garbage=4, deflate=True)
        pdf.close()
        with pymupdf.open(output) as check:
            assert len(check) == 1
            assert "INV-TEST-4102" in check[0].get_text()
            if source.stem != "baseline":
                assert "INV-OVERRIDE-9999" in check[0].get_text()


if __name__ == "__main__":
    build()
