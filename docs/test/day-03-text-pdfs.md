# Day 3 — text PDFs, three runs

Date: 2026-11-17. Commit measured: `1d0d7ac`. Environment: `live-dev`, with the corrected
scores rescored offline in `offline` from the saved replies.

What was tested, and why: whether the two-call pipeline gives stable keyed answers on all
text PDFs, and why each miss happens.

Inputs: 15 public text PDFs, 17 keyed pages, 79 owner-keyed fields per run. Run IDs
`20261117T040618822456Z`, `20261117T040940475226Z`, `20261117T041252728554Z`.

Command: `C:\venvs\harness\Scripts\python.exe scripts\environments.py live-dev -- --development --text-only`

Expected: every page completes, and every keyed miss has a named kind.

Actual:

| Measure | Run 1 | Run 2 | Run 3 |
| --- | ---: | ---: | ---: |
| Keyed fields correct, original live report | 74/79 | 73/79 | 74/79 |
| Keyed fields correct, after the explicit-null scoring fix | 77/79 | 77/79 | 77/79 |
| Facts in | 414 | 437 | 408 |
| Verified | 69 | 103 | 82 |
| Uncertain | 317 | 328 | 301 |
| Failed | 2 | 1 | 4 |

Failures, in all three runs:

- `receipt_002.order_number`, stage extraction, model miss: the model drops the printed `#`.
- `w2_001.tax_year`, stage extraction, inference correctly caught: the year comes from an
  identifier, not a printed tax-year field.

What this does not prove: general accuracy. Field definitions, answer keys and scorer rules
were adjusted while looking at these documents, so 77/79 is a development figure. It says
nothing about scanned pages, and open-fact counts vary between runs.

Follow-up: three definition wordings changed on 2026-11-18, for `form_handwritten_001` and
`form_library_001`. Those two documents need three live reruns.
