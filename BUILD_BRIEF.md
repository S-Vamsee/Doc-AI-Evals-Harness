
Build brief — rebuild the harness core around the hard rules
Read AGENTS.md first. Its rules override anything here.

Goal
One page of any kind (receipt, statement, form, newspaper, scan) goes in. Out comes a list of facts, each with evidence, a state, and a reason, plus an honest report. If an answer key exists for that page, the facts are also scored. If not, they are reported as unscored. The harness never prints a number it did not earn.

Keep, rebuild, remove
Keep: the 20 public PDFs, data/sources.json, the human answer keys, the timestamped run folders, the --compare idea, the OCR cache keyed on PDF, model digest, and prompt.
Rebuild: extraction output format, evidence checking, scoring, reporting, judge calibration.
Remove: the string-anywhere-in-text groundedness check; the 26/26 calibration as a gate; any place a field was swapped to avoid a failure.
Restore: the W-2 tax_year field. The year is printed on the page but absent from the selectable text. Keep it as a recorded failure with stage text_layer, and write it up as the real messy-document case study.
The fact record
Every extracted item, whether a single field or a relation, is one record:

{
  "fact_id": "string",
  "kind": "field | relation",
  "subject": "string or null",
  "relation": "string",
  "value": "string or null",
  "origin": "extracted | inferred",
  "evidence": { "page": 1, "quote": "exact text", "bbox": [x0, y0, x1, y1] },
  "state": "verified | uncertain | failed",
  "reason": "short plain sentence",
  "stage": "text_layer | ocr | extraction | evidence_check | normalization | answer_key | none",
  "exact": "pass | fail | unscored",
  "judge": "pass | fail | unscored",
  "human_verdict": "right | wrong | missing | null"
}
Validate every record against a schema. A record that fails validation is failed with stage extraction. human_verdict is filled in later by a person and is never written by the machine.

The pipeline (one generic path)
Read. Get the text layer with word positions. If the page has no usable text layer, render it and transcribe with the local vision model.
Extract. Ask the extractor for every fact on the page, each with an exact quote and whether it was read or inferred. If an answer key exists, also ask for its named fields. The prompt never contains answer-key values.
Check evidence by code.
Text pages: search the page for the quote. Found, and the value is contained in or normalizes from the quote: verified, with the bounding box taken from the search. Not found: uncertain.
Scanned pages: run a second, independent OCR engine that returns word boxes. Quote found by both readings: verified. Found by only one: uncertain.
inferred facts are never verified.
Score only where an answer key exists, with typed comparison per field (date, money, identifier, name, free text). The answer key states the expected type and whether prefixes such as # matter.
Report. Counts by state, failures grouped by stage, scored and unscored kept apart, run manifest, and a plain statement of what was tested.
Human review: the machine goes first, the human sees a short queue
The human never lists the facts on a page and never re-checks what code already verified. For each page the harness writes a review file containing only:

Uncertain facts, ranked so the most doubtful come first, capped at a configurable number (default 10). Facts beyond the cap stay uncertain and are reported as unreviewed. They are never promoted.
A small random sample of verified facts (default 3), to measure how often the code check itself is wrong.
Uncovered text. Code lists the lines on the page that no fact's evidence quote touches. The human glances at these and records any real fact that was missed as human_verdict: missing.
Each item shows the fact, the quote, and where it sits on the page, and needs one answer: right, wrong, or missing. The report states how many facts the human reviewed out of how many were extracted, and the error rate found in the sample.

Full human labelling of a page happens only for the small fixed calibration set (5 to 10 pages), once. It exists to prove that the short queue can be trusted. It is never part of normal use.

Work order
Step 5a, after the report writer: build the review file, the cap, the random sample, the uncovered-text list, and the reading of human verdicts back into the next report.

Do these in order. Each step is finished only when its tests pass with no network and the owner has seen the output.

Rule tests first. One test per rule in AGENTS.md, each with a broken input: a fabricated quote, a count mismatch, a simulated API error, an inferred value, a page with a hidden instruction, a missing answer key. All twelve should fail at this point.
Fact record and schema validation.
Evidence check for text pages, including bounding boxes.
Stage-tagged failure handling and the run manifest. Non-zero exit on an incomplete run.
Report writer that refuses to print when counts do not add up.
Typed scoring and updated answer keys with field types. Add fields whose correct answer is null to at least five documents.
Second OCR engine and the scan evidence check. Confirm it installs and runs on Windows, CPU only, before committing to one.
Judge recalibration. About 60 hand-labelled pairs, half of them wrong (near-misses, wrong row, changed digit, added year). Report false-accept and false-reject rates. Use a different model than the extractor.
Injection documents. At least three pages with embedded instructions, scored on whether the output changed.
One unseen page type with no answer key (for example a newspaper page) run end to end, to prove the unscored path.
Recorded-response test fixtures and CI so every push runs all rule tests for free.
README rewrite from the real outputs, including the W-2 case study and the confidence range on every accuracy figure.
Reporting numbers
Every accuracy figure is shown with its count and a confidence range (Wilson interval), for example "95 of 97, about 93% to 99%".
Cost is tokens times a price table in configuration, labelled as an estimate, with the table's source stated. Add cost per correct verified field.
Latency states what was cached and excludes nothing silently.
Not in scope
No web UI, no database, no encryption layer, no per-document-type logic, no new models beyond one extractor, one judge, one vision model, and one OCR engine.

Open decisions — ask the owner, do not decide alone
Which second OCR engine, after the Windows install check.
Which model serves as the judge.
The list of allowed relation names, or whether relations stay free-text for now.
Whether a public labelled dataset (CORD, SROIE, or FUNSD) is added for scale.
