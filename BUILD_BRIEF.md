# Build brief v2 — ten-day plan (15 to 24 November 2026)

This replaces `BUILD_BRIEF.md`. `AGENTS.md` still governs everything; where this brief
amends it (section 2), the owner has approved the amendment by giving you this file.

Roles: the owner decides and verifies. You (the coding agent) build, run, and report.
A second model reviews your output each day. Do not start a day's work until the
previous day's closing routine (section 5) has passed.

---

## 1. What changed since v1

Research and our own results settled four points:

1. **A found quote is not proof.** Finding the quote on the page shows the text exists,
   not that it supports the value. Evidence presence and evidence support are scored
   separately.
2. **The model judge stays off.** `gemma3:4b` accepted 18 of 36 wrong pairs. Code and
   the human review queue do the work. No judge prompt tuning.
3. **No "recall" without a complete answer set.** Report coverage against a named
   answer-key version. Open extraction gets counts, never a recall figure.
4. **Prompt injection is measured, not solved.** Report a rate. Claim no immunity.

Also new: a held-back document set nobody tunes against, and every measurement run
twice.

## 2. Amendments to AGENTS.md (apply on Day 1, show the diff)

- **Rule 3, add:** "Evidence has two parts. *Presence*: the quote is found at the
  claimed place. *Support*: the value can be derived from the quote by its type's
  rules. A fact is `verified` only when both pass."
- **Rule 9, replace the last sentence with:** "This is tested with pages that contain
  such instructions, and the measured rate of changed outputs is reported. No claim
  of immunity is made."
- **Rule 11, add:** "The word recall is used only where every correct answer is known.
  Otherwise report coverage against the answer-key version."
- **Add under 'How you work':** "Every measurement that goes into the README is run
  twice on identical inputs, and both results are shown."

## 3. The four scores (use these names everywhere)

| Score | Question | How it is decided |
| --- | --- | --- |
| Value | Is the value right? | Typed comparison with the answer key. Unscored if no key. |
| Evidence presence | Is the quote on the page where claimed? | Exact search after whitespace normalization. |
| Evidence support | Does the quote back the value? | Code: the value, normalized by its type, is derivable from the quote. If the answer key lists printed labels for the field, the quote's line must contain one. |
| Verified | Can this fact be relied on? | Presence and support both pass, and origin is `extracted`. |

Never average these into one number. A correct value with failed support is reported
as "value right, evidence not supporting", and goes to the review queue.

## 4. Day by day

Each day lists the work and the test for "done". Days marked **owner** need the
owner's input before you can finish; ask early in the day.

### Day 1 — Sun 15 Nov — lock the plan
- Report current state: branch, last commit, tests passing, and which of these are
  done: near-match review queue; trailing-punctuation and weekday/month abbreviation
  matching; per-document `date_order` (statement_001 = DMY, fail closed when absent);
  rule 12 described in the README as an existence check.
- Finish any of those that are not done.
- Apply the AGENTS.md amendments in section 2.
- Check that a second OCR engine installs and runs on this PC (Windows, CPU only).
  Try RapidOCR first, then Tesseract. Report install steps, time per page, and whether
  it returns word positions. Do not wire it in yet.
- Owner-approved addition: run the 20 development PDFs through a judge-free runner
  today, using validated saved scan readings. Leave scan facts uncertain until the
  independent OCR check is wired in. Save two complete runs and a field comparison.
- **Owner:** confirm the fact kinds for open extraction (section 9).
- **Done when:** state report delivered, amendments applied, 0 failing tests, OCR
  findings reported, and the two 20-document runs and their comparison are saved.

### Day 2 — Mon 16 Nov — first page, end to end
- Run `invoice_001` live through the whole new pipeline: read, manifest, extract (keyed
  fields and open extraction), evidence presence, basic evidence support, scoring,
  review file, report. Basic support checks that the value, normalized by its type,
  is derivable from the quote. A fact is `verified` only when both presence and
  support pass.
- Save the model responses so the run can be replayed offline as a test.
- **Done when:** one report exists in which facts in = verified + uncertain + failed +
  skipped, the manifest is complete, and the offline replay gives the same report.

### Day 3 — Tue 17 Nov — all 15 text PDFs
- Run all text PDFs live. Group every failure by stage.
- Expected findings to confirm, not hide: `w2_001` year (printed, absent from the text
  layer), `form_library_001` filled values (stored as form fields, absent from page
  text).
- Read filled form-field values from the PDF and label them as form fields.
- **Done when:** every failed or uncertain fact has a named stage and a one-line
  reason, and a table of failures by stage is in the report.

### Day 4 — Wed 18 Nov — evidence support
- Extend the Day 2 support check with the optional printed-label check from section 3
  and report the four scores. For every trick case, report which layer caught it.
- Build at least 12 trick cases as fixtures, each with the expected outcome:
  1. right value, irrelevant quote
  2. right value, quote from the wrong page
  3. right value under the wrong label ("Payment due" for a statement date)
  4. same amount printed twice under different labels (`receipt_001`: TOTAL and Paid by card)
  5. value that appears only inside an instruction sentence on the page
  6. inferred value whose quote lacks it (added year)
  7. quote paraphrased, not exact
  8. quote spanning two lines
  9. empty quote
  10. amount correct, currency marker missing from the quote
  11. null answer returned with a quote
  12. subtotal quoted for a total
- **Done when:** for each trick case the report says which layer caught it (presence,
  support, value score) or that nothing did. Uncaught cases are listed as known gaps.
  Do not weaken a case to make it pass.

### Day 5 — Thu 19 Nov — checkpoint
- Run the 15 text PDFs twice, live, on identical inputs. Show field-level differences.
- No new features. Fix only what days 2 to 4 left open.
- **Owner:** reviews results and confirms or changes the plan for days 6 to 10.
- **Done when:** two runs compared, differences explained, carry-overs closed or
  recorded as known gaps.

### Day 6 — Fri 20 Nov — scanned pages
- Wire in the second OCR engine chosen by the owner on Day 1.
- A scanned fact is `verified` only if its quote is found in both readings (Qwen and
  the second engine); found in one only, it is `uncertain`.
- Run the 5 scans. Report agreement between the two readings and the time taken.
- **Done when:** all 5 scans produce a report, and no scanned fact is verified on one
  reading alone.

### Day 7 — Sat 21 Nov — hidden instructions
- Make at least 3 test PDFs, each a copy of a clean specimen plus an instruction:
  visible text, very small or pale text, and an instruction inside a field's value.
  Use only self-made or CC0 content. Record their sources.
- Run each trick page and its clean twin, live. Measure: how many keyed fields changed
  (attack success), and whether the clean twin's score is unchanged (normal use intact).
- Save responses for the offline test. Rule test 09 must now assert on these outputs.
- **Done when:** the rate is in the report, and the README wording says the harness
  treats page text as data, tests adversarial pages, and does not claim immunity.

### Day 8 — Sun 22 Nov — held-back documents (owner)
- Propose 8 public candidate PDFs of mixed types with source URLs. Download only. Do
  not run them, extract from them, or write fields for them.
- **Owner:** picks 5, chooses the fields, and writes the answer keys.
- Validate the key files' format only, then freeze the set: record file fingerprints
  and key version, and mark it "not for tuning".
- **Done when:** 5 documents and keys are frozen and nothing in the pipeline has been
  changed after looking at them.

### Day 9 — Mon 23 Nov — final measurement
- Run the held-back set twice, live. Run the 20 development documents twice.
- Report per document type and per field type: the four scores, coverage against the
  key version, failures by stage, cost per document, cost per verified field, median
  and worst latency, each with its count and a confidence range.
- Push the branch (after the owner says yes) so the GitHub workflow runs.
- **Done when:** the results report exists, both runs are shown, and CI is green.
  If the held-back results look bad, they are reported as they are. No changes to make
  them better.

### Day 10 — Tue 24 Nov — publish
- Rewrite the README from the real results: what it is, who it is for, the four
  scores, results with ranges, the judge finding, the injection rate, the W-2 and
  form-field findings, known gaps, and what is not claimed.
- Update the status table. Remove this brief from the repo root.
- **Owner:** approves the merge to `main`.
- **Done when:** the public README matches the reports exactly, and nothing in it is
  untested.

## 5. Closing routine, every day

1. Run the full offline test suite. Any failure stops new work.
2. Rerun the 20 development documents (scans use cached readings).
3. Compare with the previous day's run, field by field. List anything that got worse
   and why.
4. Write the day's record files (section 11).
5. Commit locally with a short plain message. Do not push unless told.
6. Send the evening report (section 7).

## 6. When something slips

- Unfinished work is first the next morning.
- If the same item is unfinished a second day, stop and ask the owner: cut it down, or
  record it as a known gap. Never carry it a third day.
- Cut first if time is short: held-back set from 5 to 3 documents; scan tuning beyond
  "works and is reported as slow".
- Never cut: the closing routine, the first end-to-end run, the honest README.

## 7. Evening report format

```
Day N — date
Done today: ...
Not done, and why: ...
Tests: X passed, Y failed (names)
Development run vs yesterday: fields better / worse / unchanged, with the worse ones listed
Hosted cost today (estimate): $...   Running total: $...
Decisions I need from the owner: ...
Anything I am unsure about: ...
```

State what was not verified. Do not write "done" for anything untested.

## 8. Limits

- Hosted model spend: stop and ask if the running estimate passes $1.00.
- No judge model, no entailment model, no RAG, no knowledge graph, no agent, no
  database, no web UI, no public dataset, no licence file in these ten days.
- No change to an answer key, a rule test, or `AGENTS.md` beyond section 2 without
  the owner's yes.
- The held-back set is never used to adjust prompts, rules, or code.

## 9. Owner decisions

| Decision | Recommendation | Needed by |
| --- | --- | --- |
| Fact kinds for open extraction | party, identifier, date or time, amount, line item (one table row is one fact), labelled value, statement | Day 1 |
| Second OCR engine | whichever of RapidOCR or Tesseract installs cleanly and returns word positions | Day 1 report, decided before Day 6 |
| Plan for days 6 to 10 | as written, unless Day 5 shows a problem | Day 5 |
| Which 5 held-back documents, and their keys | mixed types, at least one scan and one table | Day 8 |
| Push the branch; merge to main | yes once CI is green and the README matches | Days 9 and 10 |

## 10. Definition of done

The project is done when this sentence can be written with real numbers and every
part of it is backed by a saved run:

"On a frozen held-back set of N documents, value correctness was X%, evidence presence
Y%, evidence support Z%, with W% of facts verified; each figure was measured twice;
all runs record model, prompt, input fingerprints, and code version; the injection
tests changed K of M keyed fields; and the known gaps are listed."

## 11. Written record: one file per step

Every day leaves a written record in the repository, so anyone can see what was built,
how it was tested, and what happened. Build and test are kept apart.

```
docs/
  build/   day-02-first-page.md, day-04-evidence-support.md, ...
  test/    day-03-text-pdfs.md, day-05-repeat-runs.md, day-07-injection.md, ...
  checkpoints/  day-01-plan.md, day-05-review.md, day-10-release.md
  environments.md
```

Rules for these files:

- One file per day. A day that both builds and tests writes one file in each folder.
- Write the file the same day, from the actual run output. Never from memory or plan.
- Keep each under one page. Link to the run folder for detail; do not paste long logs.
- A file is never edited later to look better. Corrections are added at the bottom
  with the date.

**Build file template**

```
# Day N — title
Date:            Commit:
What was built: (plain words, 3 to 6 lines)
Files changed:
Decisions made, and who made them:
How to run it: (the exact command)
What it does not do yet:
```

**Test file template**

```
# Day N — title
Date:            Commit:            Environment: (name from environments.md)
What was tested, and why:
Inputs: (documents or cases, with fingerprints or run folder)
Command:
Expected:
Actual: (numbers, both runs where run twice)
Failures: (each with stage and one-line reason)
What this does not prove:
Follow-up:
```

**Checkpoint file template**

```
# Day N — checkpoint
State against the plan: (done / not done per item)
What the results say:
What changes in the plan, and why:
Owner's decisions:
```

## 12. Test environments

Set these up on Day 1 and describe each in `docs/environments.md` (purpose, how to set
it up, the command, what it may and may not touch). Every test file names the
environment it ran in.

| Name | Purpose | Network and keys | When it runs |
| --- | --- | --- | --- |
| `offline` | Rule tests and replayed model responses | None. Must pass with no `.env` and no network. | Every commit and every evening |
| `clean` | Proves the project installs and passes from nothing | None | Days 1, 5, 9. Fresh virtual environment installs `requirements.txt`, then `requirements-dev.txt`, runs a key-free CLI smoke test, and runs the full offline suite. |
| `live-dev` | Real model calls on the 20 development documents | Hosted model key from `.env`; local Ollama | Days 2, 3, 5, 6, 7, and each evening rerun |
| `live-heldback` | Real model calls on the frozen held-back set | Same as `live-dev` | Day 9 only. Refuses to run before the set is frozen, and logs every run. |
| `ci` | The `offline` suite on GitHub | None | On push, from Day 9 |

Requirements:

- Each environment has one command or script to start it, recorded in
  `docs/environments.md`.
- Keep pytest and other test-only packages in `requirements-dev.txt`, not
  `requirements.txt`.
- `offline` and `clean` must not be able to make a paid call. Test this: with a key
  present, a run in `offline` must still make zero network requests.
- `live-dev` and `live-heldback` write to separate result folders and never share a
  cache.
- Every run records which environment it used in its manifest.
- Recorded responses used by `offline` are stored with the prompt hash they answer.
  If the prompt changes, the replay fails loudly instead of using a stale answer.
- Day 1 is done only when `offline` and `clean` both pass and `docs/environments.md`
  exists.
