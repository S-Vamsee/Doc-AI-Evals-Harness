# Day 3 — tryout command

Date: 2026-11-18.

What was built: a command that runs any text PDF through the current pipeline with no answer
key. Each page gets a readable `trace.md` showing the text read, what the model was asked,
what it returned, what each check decided and why, the counts, and the estimated cost. Every
result is labelled "extracted, unscored".

Files changed: `src/tryout.py`, `src/core_pipeline.py`, `run_eval.py`, `scripts/environments.py`,
`tests/test_tryout.py`, `tests/test_field_definitions.py`, `data/field_definitions.md`, `.gitignore`.

Decisions made, and who made them: the owner approved three neutral definition wordings.
Tried documents are remembered by fingerprint only in `data/tryout_registry.json`, and the
held-back environment refuses any of them.

How to run it:

`C:\venvs\harness\Scripts\python.exe scripts\environments.py live-dev -- --tryout path\to\file.pdf`

Add `--fields total_amount,due_date` to ask for named fields. Results go to `results/tryouts/`.

What it does not do yet: scanned pages are refused or skipped until the second reading is
wired in. It gives no accuracy figure, because no answer key is used.
