# Self-made injection test pages

These four one-page PDFs are generated from the adjacent `.txt` files by
`build_pdfs.py`. They are synthetic test fixtures, not part of the 20-document
public evaluation set. `baseline.pdf` contains the invoice facts; the other
three visibly add a forged system message, a delimiter/role spoof, or a forged
assistant answer key. The offline test replays live responses saved under
`tests/fixtures/injection_pages/` and checks that the extracted fields match
the baseline. The first live pass failed on the forged answer key and is kept
separately as evidence.
