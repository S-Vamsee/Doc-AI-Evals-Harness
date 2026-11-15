# Day 1 — checkpoint

State against the plan: V2 brief and approved AGENTS amendments applied; fact kinds confirmed and tested; five environment entry points created; `offline` and `clean` each passed 88 tests; CI entry point passed 88; OCR probe completed. Day 1 closing routine and local commit are not done.

What the results say: The new environment can run the tests without keys or network. Both RapidOCR and Tesseract return positioned words on one scan; Tesseract was faster in this single-page probe. The result does not establish which is more accurate.

What changes in the plan, and why: Owner's Day 2 basic support gate and Day 4 printed-label challenge split are in `BUILD_BRIEF.md`. The daily closing routine cannot rerun 20 documents through the new core yet; the old full runner invokes the disabled judge. This needs an owner decision, not an implicit workaround.

Owner's decisions: Clean installs runtime then dev requirements and runs smoke plus offline suite. Seven open-extraction kinds and two classification rules approved. Tesseract selection from the earlier owner answer remains recorded; it has not been wired into the new core.

Correction, 2026-11-15: The owner selected a judge-free 20-document runner for Day 1 instead of deferring the closing rerun. It now runs on all 20 documents (22 keyed pages), with two complete live passes and a field-level comparison. Final offline and clean gates each pass 93 tests. Four keyed values worsened on the repeat, so model variability is a finding, not a score to hide. Day 1 still needs the pre-commit independence/source check, local commit, and evening report. Day 2 basic support and Day 4 trick cases remain scheduled.

Correction, 2026-11-15 (final gate): The final code passes 96 offline, 96 clean, and 96 local CI tests. Its matched live pair reports 5 better and 1 worse keyed fields; the W-2 social-security-wages miss is the named regression. Pre-commit scan found no excluded terms in repo or PDF text, no tracked deployment codename, 20 public HTTPS source records for 20 PDFs, and 20 unchanged owner keys. Local commit and evening report follow. The verified label remains provisional until the Day 2 type-normalized support gate is built.
