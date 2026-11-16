# Self-made injection test pages

These four one-page PDFs are generated from the adjacent `.txt` files by
`build_pdfs.py`. They are synthetic test fixtures, not part of the 20-document
public evaluation set. `baseline.pdf` contains the invoice facts; the other
three visibly add a forged system message, a delimiter/role spoof, or a forged
assistant answer key. The offline tests replay live responses saved under
`tests/fixtures/injection_pages/`. `recordings.json` and
`test_injection_replay.py` cover the legacy one-call path. The first legacy
live pass failed on the forged answer key and is kept separately as evidence.
`current_two_call_recordings.json` and `test_injection_two_call.py` cover the
current keyed/open two-call path and compare all three keyed fields with the
baseline on each attack page.
