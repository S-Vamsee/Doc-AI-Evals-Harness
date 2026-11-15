# Day 1 — environment and OCR checks

Date: 2026-11-15  
Commit: pending  
Environment: `offline`, `clean`, `ci`; isolated local OCR probe.

What was tested, and why: The offline launcher and CI launcher ran the full suite; a fresh clean venv installed both requirements files from a local wheelhouse without network, passed a key-free CLI smoke test, then ran the suite. A process with a fake API key was blocked at socket connect. Both local OCR engines read one scan and returned word boxes.

Inputs: 88 repository tests; public `scan_invoice_001.pdf`, SHA-256 `605D7CBE6BEFF3F26DD0F11DBF23179873EE927244DBFCD0446E6052750EDE5F`, page 1 at 150 DPI. Source: https://filedone.ai/sample-files/sample-scanned-invoice.pdf.

Commands: `C:\venvs\harness\Scripts\python.exe scripts\environments.py offline`; `... scripts\environments.py clean`; `... scripts\environments.py ci`; `C:\venvs\harness-ocr-probe\Scripts\python.exe scripts\probe_ocr.py data\pdfs\scan_invoice_001.pdf`.

Expected: 0 failing tests; no network in offline/clean/CI; one positioned OCR reading per engine.

Actual: Offline 88 passed; clean CLI smoke passed and 88 passed; CI 88 passed. Held-back entry refused to start because no frozen set exists. RapidOCR 3.10.0 with ONNX Runtime CPU: 182 positioned words, 3.939s first call and 2.673s second. Tesseract 5.4: 190 positioned words, 1.273s and 1.267s. No hosted model call was made.

Failures: None in the tests or OCR probe. The Day 1 development rerun is blocked at the runner stage: the legacy 20-document command calls the disabled judge, while the new core supports only a text page and scan OCR is scheduled for Day 6.

What this does not prove: One scan's word counts are not an OCR accuracy comparison. A Python socket guard is not a system firewall. The live and held-back environments were not run.

Follow-up: Owner must resolve how section 5's 20-document closing rerun applies before the new all-document core exists. Then run the closing comparison and commit locally.

Correction, 2026-11-15: Owner selected the full runner. Final `offline`, `clean`, and local `ci` each passed 93 tests with zero failures. Two complete live development passes used identical PDF, answer-key, prompt, and code fingerprints. Pass A: 449 facts (32 verified, 413 uncertain, 4 failed), 95/103 keyed values exact. Pass B: 444 facts (33 verified, 397 uncertain, 14 failed), 92/103 exact. Field comparison: 1 better, 4 worse, 97 unchanged, 1 changed without a score flip. The worse fields are `notice_001` interruption_date, start_time, end_time (all became null), and `w2_001` federal_income_tax_withheld (the model chose 1,160.00 instead of 9,200.00). The printed text contains both W-2 amounts; no key was changed. There was no previous-day run of this new core, so the comparison is between two same-day passes. See `Codex/reports/day-01/comparison.md` and the two run reports for field details. OCR and scan verification remain Day 6 work.

Correction, 2026-11-15 (final measurement): After two generic fixes and the expanded code fingerprint, the final `offline`, `clean`, and local `ci` environments each passed 96 tests. The final matched live pair covered 20 documents and 22 keyed pages on identical inputs, prompts, and code. Run 1: 439 facts (33 verified, 406 uncertain, 0 failed), 90/103 exact. Run 2: 445 facts (37 verified, 399 uncertain, 9 failed), 94/103 exact. Field comparison: 5 better, 1 worse, 97 unchanged. The worse field is `w2_001` social_security_wages, 80,000.00 in run 1 and null in run 2. Nine failed facts in run 2 are line items missing columns. The stage is extraction. These are reported as findings; no key or rule test was changed. The final comparison and manifests are under `Codex/reports/day-01/final/`.
