# Day 2 — two-call extraction and evidence support

Date: 2026-11-15
Commit: recorded in local Git history after this file was written.

What was built: Keyed fields and open facts now use separate calls. The keyed JSON is validated for every requested name; explicit null, omission, and duplication remain distinct. The quote instruction asks for the full printed label-and-value phrase or line. Text evidence needs a located quote and type-normalized value support. A bare value gets `role_not_printed`, remains uncertain, and is sampled for review. Nulls are scored as abstentions and excluded from uncertainty and review. The old role overlap is labelled a lexical role hint.

Files changed: `src/core_pipeline.py`, `src/policy.py`, `src/review.py`, `src/development_run.py`, `run_eval.py`, `scripts/summarize_day2.py`, `scripts/compare_daily.py`, `scripts/export_test_inventory.py`, new offline tests and recorded invoice responses.

Decisions made: The owner required two calls, explicit keyed-field outcomes, earliest root-cause stages, and the Day 2 A–F order. No answer key was changed. The owner has three separate key rulings pending.

How to run: `python scripts/environments.py offline`; `python scripts/environments.py live-dev -- --development --text-only` for the 15 text PDFs; `python scripts/environments.py live-dev -- --development` for all 20.

What it does not do yet: The role hint is not a semantic role check. Cached scans do not receive independent OCR verification. The judge remains disabled. The new two-call contract causes repeated keyed names in open output; these are saved as extraction failures, not hidden.
