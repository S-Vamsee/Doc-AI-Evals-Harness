# Day 1 — environment setup

Date: 2026-11-15  
Commit: pending; closing routine has a plan conflict.

What was built: The v2 brief now uses the owner's clean and evidence-support decisions. The approved AGENTS amendments and fact-kind rules are recorded. The extraction prompt accepts the seven named kinds and `unclassified`; line items carry columns. The new environment launcher separates live result roots and blocks network in offline, clean, and CI. The CI workflow uses that launcher.

Files changed: `BUILD_BRIEF.md`, `AGENTS.md`, `src/policy.py`, `src/core_pipeline.py`, `src/page_eval.py`, `run_eval.py`, `.github/workflows/tests.yml`, `scripts/`, `tests/test_fact_kinds.py`, `tests/test_environments.py`, `docs/`.

Decisions made, and who made them: Owner chose clean to install runtime then dev requirements, run CLI smoke and all offline tests; owner moved the basic support gate to Day 2; owner chose seven fact kinds, most-specific precedence, and an unclassified count. Existing owner choice of Tesseract remains in force.

How to run it: `C:\venvs\harness\Scripts\python.exe scripts\environments.py offline` and `C:\venvs\harness\Scripts\python.exe scripts\environments.py clean`.

What it does not do yet: No live model call, Day 2 support gate, held-back set, or Day 6 OCR wiring was done. The legacy full 20-document runner still invokes the disabled judge; the Day 1 closing rerun cannot be used as written.

Correction, 2026-11-15: The owner chose to build the judge-free 20-document runner on Day 1. `src/development_run.py` now processes every answer-key page, preserves validated cached scan readings, records incomplete runs, and writes combined manifests. The first live pass exposed a generic line-item shape mismatch; its fourteen incomplete pages remain saved. After the parser fix, two complete live passes covered 20 documents and 22 keyed pages each without judge calls. The new comparison command requires identical input, prompt, and code fingerprints. The Day 2 evidence-support gate is still pending.

Correction, 2026-11-15 (final measurement): The manifest fingerprint now covers the runner and review policy. The live extractor allows a larger output and records a named truncation failure. Failed scan line items keep their failure state. Two later complete runs with this final code are saved under `results/environments/live-dev/development_runs/20261115T102357881486Z` and `20261115T102639444345Z`; their reader copies are under `Codex/reports/day-01/final/`.
