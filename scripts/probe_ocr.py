"""Measure two local OCR engines on one rendered PDF page; no pipeline wiring."""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
import subprocess
import tempfile
import time

import pymupdf


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--tesseract", type=Path,
                        default=Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="harness-ocr-") as folder:
        image = Path(folder) / "page.png"
        with pymupdf.open(args.pdf) as pdf:
            page = pdf[0]
            pix = page.get_pixmap(matrix=pymupdf.Matrix(150 / 72, 150 / 72), alpha=False)
            pix.save(image)
            width, height = pix.width, pix.height

        from rapidocr import RapidOCR

        engine = RapidOCR()
        rapid_times = []
        rapid_words = []
        rapid_examples = []
        rapid_units_with_spaces = []
        for _ in range(2):
            started = time.perf_counter()
            result = engine(str(image), return_word_box=True)
            rapid_times.append(round(time.perf_counter() - started, 3))
            positioned = []
            for group in (result.word_results or []):
                items = [group] if len(group) >= 3 and isinstance(group[0], str) else group
                positioned.extend(item for item in items if len(item) >= 3
                                  and isinstance(item[0], str) and item[0] and item[2])
            rapid_words.append(len(positioned))
            rapid_examples = [item[0][:48] for item in positioned[:8]]
            rapid_units_with_spaces.append(sum(" " in item[0] for item in positioned))

        tesseract_times = []
        tesseract_words = []
        for _ in range(2):
            started = time.perf_counter()
            output = subprocess.run([str(args.tesseract), str(image), "stdout", "tsv"],
                                    capture_output=True, text=True, check=True)
            tesseract_times.append(round(time.perf_counter() - started, 3))
            rows = list(csv.DictReader(io.StringIO(output.stdout), delimiter="\t"))
            tesseract_words.append(sum(1 for row in rows if row.get("text", "").strip()
                                       and row.get("left") and row.get("top")
                                       and row.get("width") and row.get("height")))

    print(json.dumps({"pdf": args.pdf.name, "dpi": 150,
                      "image_pixels": [width, height],
                      "rapidocr": {"seconds_per_page": rapid_times,
                                   "positioned_words": rapid_words,
                                   "units_with_spaces": rapid_units_with_spaces,
                                   "examples": rapid_examples},
                      "tesseract": {"seconds_per_page": tesseract_times,
                                    "positioned_words": tesseract_words}}, indent=2))


if __name__ == "__main__":
    main()

