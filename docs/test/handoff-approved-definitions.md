# Test-chat handoff: approved definitions and three runs

Branch: `rebuild/core-rules`. The builder's current commit contains the owner-approved definition loading, two owner-approved answer-key corrections, the saved two-call instruction replays, a null-abstention regression fix, and the three-run comparison in `docs/test/definitions-three-runs.md`. Day 4 has not started.

The five shared rules and 103 field definitions have one source, `data/field_definitions.md`. `run_eval.py` loads them into the in-memory answer keys; the keyed prompt and each page's `review.json` use the same source. The physical key JSON files retain their values and types without duplicating definitions.

The 15 text PDFs were run live three times with the definitions. All 17 keyed and 17 open page calls completed in each run. The live reports originally showed 74/79, 73/79, 74/79. A newly added test caught an explicit-null scoring error; the fix was applied to the saved replies without new model calls or answer changes. The corrected replay is 77/79 in each run. The two persistent keyed misses are `receipt_002.order_number` (dropped `#`) and `w2_001.tax_year` (inference caught). Open extraction is experimental and its per-run counts are in the comparison report.

The current offline suite passes 140 tests. Four fresh live Rule 09 runs—baseline plus three self-made instruction pages—returned the same three keyed values, with 0/9 attack fields changed. Their raw replies and prompt hashes are in `tests/fixtures/injection_pages/current_two_call_recordings.json`. The old-path replays remain labelled legacy elsewhere in the repo.

The builder scanned the current tracked and new files and all reachable branch-history blobs for credential patterns, the private deployment label, Windows username paths, and the known excluded names. The focused scan found zero matches. All 20 PDFs have a public source URL and an owner-provided human key. The hosted reference cost estimate is separate from any billed amount. There was no recorded proof of a pre-push scan for the earlier `f2967ae` push.

Pending after this handoff: independent test-chat verdict on this commit; Day 4 printed-label work; scan-path work; judge remains disabled. The three corrected scores are saved-reply rescoring, not three fresh live runs under the final report-only code change.
