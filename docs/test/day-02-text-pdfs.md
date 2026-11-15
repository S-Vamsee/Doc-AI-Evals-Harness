# Day 2 — text PDFs and offline replay

Date: 2026-11-15
Commit: recorded in local Git history after this file was written.
Environments: `offline`, `live-dev`.

What was tested, and why: The offline suite checks the keyed contract, evidence support, abstentions, review sampling, W-2 text-layer causes, text-only selection, saved-run summaries, and a recorded live invoice replay. Three independent live runs measured the 15 text PDFs with the same code and prompt. The closing run covered all 20 PDFs with cached scan readings.

Inputs: 112 offline cases; public invoice `invoice_001` with saved keyed/open responses; 15 public text PDFs (17 keyed pages, 79 fields); 20 public PDFs (22 keyed pages, 103 fields). The three text run IDs are `20261115T110450049536Z`, `20261115T110735883827Z`, and `20261115T111057430397Z`. The closing run is `20261115T111942521489Z`. Manifests record PDF/key hashes, prompt hash, and code version.

Commands: `python scripts/environments.py offline`; `python scripts/environments.py live-dev -- --development --text-only` three times; `python scripts/environments.py live-dev -- --development` once.

Expected: Zero offline failures; every incomplete page and field has a named stage and reason; facts tally; no scan verified from one OCR reading.

Actual: 112/112 offline tests passed. The saved live invoice replay reproduced 25 facts (5 verified, 20 uncertain) and 5/5 keyed score. Text runs scored 38/79, 32/79, and 38/79; complete pages were 5/17, 4/17, and 4/17. The middle run's truncated page had six keyed fields counted as extraction failures in the comparison. The full 20-document closing run scored 53/103 and completed 7/22 pages. Day 1 versus Day 2 on identical PDF/key bytes: 3 better, 44 worse, 54 unchanged, 2 value changes without a score flip; code and prompt changed.

Failures: The open call repeated keyed relation names 35–36 times per text run; those fields failed at extraction as `duplicate`. One open response reached its output limit in text run 2. The full closing run recorded 44 duplicate failures. W-2 `tax_year` and `federal_income_tax_withheld` have no printed role labels in the selectable text; their failed keyed answers report `text_layer` as the earliest root cause.

What this does not prove: The diagnostic scores do not establish accuracy on completed documents or full-page recall. The role hint is lexical only. The cached scans are not independently verified. The three runs were incomplete, and the cross-day comparison changed the measurement contract.

Follow-up: The test chat should inspect the 112-row inventory and the duplicate failures. The owner will send three key rulings separately. No key was edited for this run.
