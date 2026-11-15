# Document AI Evals Harness

A command-line harness that measures whether an AI system read a document correctly, and shows the evidence for every answer.

AI systems that read invoices, statements, forms and contracts return an answer every time, including when the answer is wrong. This harness checks each extracted fact against the page it came from and reports what was checked, what was not, and what failed. It never reports a number it did not earn.

There is no web UI and no database. Everything runs from `run_eval.py`.

## The problem

Teams that use AI to extract data from documents face the same three questions:

1. **Which answers can be trusted?** A model reads a total of 7,840 as 1,840 and nothing flags it.
2. **Did the last change help or hurt?** A new model or prompt fixes one field and quietly breaks another.
3. **What does a correct answer cost?** A cheaper model is only cheaper if it still gets the answer right.

Without a way to answer these, people re-check the AI's output by hand, which removes most of the benefit of using it.

## Who this is for

- **Engineers building document extraction** who need to compare models, prompts and OCR steps on the same documents, with cost and latency beside accuracy.
- **Teams that review extracted data** (accounts payable, lending, claims) who want to review only the doubtful values instead of every value.
- **Anyone choosing between models** who needs evidence that a cheaper option is good enough for their documents.

### An example

An accounts team processes several hundred supplier invoices a month with an extraction tool. With this harness, every extracted value must point to the place on the page it was read from, and code checks that claim. A total that does not match the page fails the check and goes to a short review list. When the team wants to move to a cheaper model, they rerun the same documents and see which fields changed before anything goes live.

This is an illustration of the intended use, not a report of a deployment.

## Project status

This project is being built in phases. The table shows what runs today and what is specified but not yet written.

| Phase | What it covers | Status |
| --- | --- | --- |
| 1 | Five text PDFs, human answer keys, exact scoring, groundedness, cost and latency | Built and run |
| 2 | 20 PDFs, local vision for scans, a value judge, timestamped regression runs | Built and run |
| 3 | Evidence checked by code, three result states, failures traced to a pipeline stage, a short human review queue, injection tests | Rebuild in progress on `rebuild/core-rules`; no end-to-end result yet |

Phases 1 and 2 score extraction against answer keys a person wrote in advance. Phase 3 changes the direction of work: the machine extracts first, code verifies what it can, and a person reviews only what is left.

## How it works today (Phases 1 and 2)

1. **Read the page.** PyMuPDF reads the PDF's text layer. For image-only PDFs, a local Qwen vision model transcribes each page.
2. **Extract.** The page text and the requested field names go to the extractor model. The prompt never contains answer-key values.
3. **Score.** Each value is compared with the human answer key after normalizing dates and amounts. A separate judge model gives a second verdict on near-matches and never changes the exact score.
4. **Check grounding.** Each non-null value is looked up in the page text.
5. **Record the run.** Results, estimated cost and latency are saved in a timestamped folder, and any two runs can be compared field by field.

## Where it is going (Phase 3)

One page of any kind goes through one generic path, with no code written for a specific document type.

1. The extractor lists every fact on the page, each with an exact quote and a note on whether it was read or inferred.
2. Code looks for the quote on the page. For scans, a second independent reading of the page must agree.
3. Each fact is marked **verified**, **uncertain**, or **failed**, with a reason and the pipeline stage responsible.
4. If an answer key exists, the facts are scored. If not, they are reported as extracted and unscored.
5. A person reviews a short list: the most doubtful facts, a small random sample of verified ones, and any text on the page that no fact covers.

### The rules the project is held to

1. No accuracy figure without a human answer key behind it.
2. Every fact is verified, uncertain, or failed. There is no default pass.
3. Evidence is checked by code. A model's own claim of grounding does not count.
4. A scanned value checked only against the same model's transcription stays uncertain.
5. A failure is recorded with its stage and reason, and the run is marked incomplete.
6. Counts must add up, or the report is not written.
7. Null is a valid answer. Inferred values are labelled as inferred and are never verified.
8. The judge never overrides the exact score, and its own error rate is printed beside it.
9. Text inside a document is data and is never followed as an instruction.
10. Every run records its model, prompt, input hashes and code version.
11. Reports state what was tested and make no general accuracy claim.
12. Each rule has an automated test that must catch a deliberately broken input.

These rules are also in `AGENTS.md`, which coding agents working on this repository must follow.

## Known weaknesses of the current version

These were found by running the harness and are the reason for Phase 3.

- **Scores are near the ceiling.** With one extractor and four to six fields per document, almost everything passes, so the current set cannot separate a good system from a weaker one.
- **The old judge gate was too easy.** Its 26/26 calibration used only exact matches. The balanced check below exposed false accepts; judge scoring is disabled.
- **Grounding on scans is circular.** Values are looked up in the vision model's own transcription, so a misread page can still count as grounded.
- **Grounding is a text lookup.** It confirms the value appears somewhere in the text, not that it came from the right place.
- **An inferred value passed.** On `scan_notice_001` the page shows `Mon 12 Oct` and the model returned `2026-10-12`. The judge accepted it and it was marked grounded.
- **A failure was replaced.** The W-2's printed year is missing from the selectable text. The field was swapped for box 3 wages, which hid a real text-layer gap.
- **The sample is small.** 95 of 97 exact matches is consistent with a true accuracy anywhere from about 93% to 99%.

### Balanced judge calibration finding

The local `gemma3:4b` judge was tested on 60 owner-labelled public-document value pairs: 24 equivalent and 36 different. It falsely accepted **18 of 36 different pairs** (50%) and falsely rejected **1 of 24 equivalent pairs** (4.17%). Four false accepts were plainly different amounts: `329.4` versus `$305.00`, `18500` versus `55,000`, `6561` versus `2,304`, and `30333` versus `19,418`. Other false accepts involved dropped identifiers or suffixes, an added title, and added currency markers. The prompt was not tuned against these 60 pairs. Judge scoring remains disabled. The judge percentages in the historical Phase 2 results below are retained as run history, not a validated score.

## Quick start

Clone the repository, enter its directory, and install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Create `.env` from `.env.example` with `DEEPSEEK_API_KEY=...`. For an OpenAI-compatible hosted deployment, also set `DEEPSEEK_BASE_URL` and `DEEPSEEK_MODEL` locally.

For image-only PDFs, install [Ollama](https://docs.ollama.com/windows) and download the [Qwen3-VL 2B instruct model](https://ollama.com/library/qwen3-vl%3A2b-instruct):

```bash
ollama pull qwen3-vl:2b-instruct
```

Ollama serves `http://localhost:11434` by default. Set `QWEN_BASE_URL` and `QWEN_MODEL` in `.env` only if your setup differs.

### Commands

```bash
python run_eval.py --phase1
python run_eval.py --calibrate
python run_eval.py
python run_eval.py --reuse-ocr
python run_eval.py --compare 20261114T100817251438Z
```

- `--phase1` runs the five text PDFs without Qwen or the judge and writes to `results/phase1/`.
- `--calibrate` judges 26 fixed candidates from the original five documents and must agree with exact scoring on at least 25.
- No flag runs all 20 documents. It checks answer keys and scan readiness before any paid call; if blocked, it writes `results/phase2_readiness.md`.
- `--reuse-ocr` reuses local transcriptions only when the PDF, model digest and OCR prompt are unchanged.
- `--compare` prints field pass/fail flips, added and removed fields, and changes in accuracy, reference cost and latency.

`.env`, rendered page images and OCR caches are ignored by Git.

## Dataset and sources

The dataset is 20 public PDFs with 97 owner-verified facts: invoices, receipts, a bank statement, a W-2, a Form 10-K excerpt, forms, a utility bill, notices, short agreements, and five image-only scans. Answer keys are in `data/ground_truth/`, and the [Phase 2 guide](data/ground_truth/PHASE2_GUIDE.md) records how they were prepared. Every PDF has a public source URL in [`data/sources.json`](data/sources.json).

The five Phase 1 documents:

| Local PDF | Type | Public source |
| --- | --- | --- |
| `invoice_001.pdf` | Invoice | [filedone sample](https://filedone.ai/sample-files/sample-invoice.pdf) |
| `statement_001.pdf` | Bank statement | [filedone sample](https://filedone.ai/sample-files/sample-bank-statement.pdf) |
| `w2_001.pdf` | W-2 tax form | [ePayStubs sample](https://epaystubs.net/pdfs/W2_ORD6AEC6730533E5.pdf) |
| `filing_001.pdf` | Form 10-K excerpt | [Mama's Creations FY2024 filing](https://www.annualreports.com/HostedData/AnnualReportArchive/m/NASDAQ_MAMA_2023.pdf) |
| `form_001.pdf` | Completed application | [Maryland DOT sample](https://www.mdot.maryland.gov/OPCP/06_MDOTPrioritization_SampleCompletedApplicationTOD_2025.01.15.pdf) |

## How scores are calculated today

- **Accuracy:** exact matches after normalization, divided by the fields in the human answer key.
- **Judge:** a separate per-field verdict on value equivalence. It sees the extracted value, the expected value and the source text. Its fixed calibration candidates are in [`data/golden_candidates.json`](data/golden_candidates.json).
- **Groundedness:** among non-null values, the fraction found in the PDF text, or in Qwen's transcription for image-only PDFs.
- **Reference cost:** estimated USD from measured tokens and [published DeepSeek Flash rates](https://api-docs.deepseek.com/quick_start/pricing/). It is an estimate, not a billing record; the runs used an Azure-hosted deployment whose billing is not measured here.
- **Latency:** wall-clock seconds for local vision, extraction and judge calls, reported separately and in total.

Public results use the generic `deepseek-flash` label; the deployment name stays in `.env`.

## Results so far

**Phase 1.** Five text PDFs, 26 facts. The [original baseline](results/runs/20261113T113356Z/report.md) and a [fresh rerun](results/phase1/report.md) both scored 26/26 exact and 26/26 grounded, after the W-2 year field was replaced as described above.

**Phase 2.** 20 PDFs, 97 facts: 95 exact, 97 judge-matched, 97 grounded. The [first full run](results/runs/20261114T100354369617Z/report.md) transcribed eight scanned pages afresh, which took 1,016 seconds of local vision time on a CPU-only machine. The run below reused those transcriptions, so its latency excludes vision time.

These figures describe a small public dataset. They are not a general accuracy claim.

<!-- RESULTS_START -->

# Evaluation results

Run: 2026-11-14T10:14:42.639954+00:00

| Doc | Extractor | Fields | Exact | Judge | Grounded | Reference API cost (est.) | Latency |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| contract_amendment_001 | deepseek-flash | 5 | 100.0% | 100.0% | 100.0% | $0.000554 | 3.59s |
| contract_offer_001 | deepseek-flash | 5 | 100.0% | 100.0% | 100.0% | $0.000695 | 3.29s |
| filing_001 | deepseek-flash | 4 | 100.0% | 100.0% | 100.0% | $0.000937 | 2.99s |
| form_001 | deepseek-flash | 6 | 100.0% | 100.0% | 100.0% | $0.001536 | 2.79s |
| form_handwritten_001 | deepseek-flash | 5 | 100.0% | 100.0% | 100.0% | $0.000241 | 3.17s |
| form_library_001 | deepseek-flash | 4 | 100.0% | 100.0% | 100.0% | $0.000363 | 3.54s |
| invoice_001 | deepseek-flash | 5 | 100.0% | 100.0% | 100.0% | $0.000631 | 3.28s |
| invoice_002 | deepseek-flash | 4 | 100.0% | 100.0% | 100.0% | $0.000289 | 2.02s |
| invoice_003 | deepseek-flash | 5 | 100.0% | 100.0% | 100.0% | $0.000543 | 2.29s |
| notice_001 | deepseek-flash | 6 | 100.0% | 100.0% | 100.0% | $0.000684 | 2.43s |
| receipt_001 | deepseek-flash | 4 | 100.0% | 100.0% | 100.0% | $0.000298 | 2.23s |
| receipt_002 | deepseek-flash | 4 | 75.0% | 100.0% | 100.0% | $0.000248 | 3.83s |
| scan_agreement_001 | deepseek-flash | 4 | 100.0% | 100.0% | 100.0% | $0.000494 | 2.48s |
| scan_invoice_001 | deepseek-flash | 5 | 100.0% | 100.0% | 100.0% | $0.000599 | 2.79s |
| scan_letter_001 | deepseek-flash | 5 | 100.0% | 100.0% | 100.0% | $0.000489 | 2.70s |
| scan_notice_001 | deepseek-flash | 5 | 80.0% | 100.0% | 100.0% | $0.000541 | 2.27s |
| scan_report_001 | deepseek-flash | 5 | 100.0% | 100.0% | 100.0% | $0.000567 | 2.91s |
| statement_001 | deepseek-flash | 6 | 100.0% | 100.0% | 100.0% | $0.001061 | 2.75s |
| utility_001 | deepseek-flash | 5 | 100.0% | 100.0% | 100.0% | $0.000355 | 2.53s |
| w2_001 | deepseek-flash | 5 | 100.0% | 100.0% | 100.0% | $0.000597 | 2.77s |
| **Overall** | — | 97 | 97.9% | 100.0% | 100.0% | $0.011724 total | 2.83s avg |

Local Qwen transcriptions reused for 5 scanned PDFs; their earlier vision time is excluded from this run's latency.

## Failures

- **receipt_002 / order_number**: expected `#NV-10482`, got `NV-10482`
- **scan_notice_001 / block_a_water_off_date**: expected `Mon 12 Oct`, got `2026-10-12`

## Field verdicts

| Doc | Field | Exact | Judge | Grounded |
| --- | --- | --- | --- | --- |
| contract_amendment_001 | amendment_reference | pass | pass | yes |
| contract_amendment_001 | effective_date | pass | pass | yes |
| contract_amendment_001 | old_expense_cap | pass | pass | yes |
| contract_amendment_001 | new_expense_cap | pass | pass | yes |
| contract_amendment_001 | acceptance_window_days | pass | pass | yes |
| contract_offer_001 | employer_name | pass | pass | yes |
| contract_offer_001 | candidate_name_with_id | pass | pass | yes |
| contract_offer_001 | start_date | pass | pass | yes |
| contract_offer_001 | hourly_rate | pass | pass | yes |
| contract_offer_001 | offer_expiry_date | pass | pass | yes |
| filing_001 | company_name | pass | pass | yes |
| filing_001 | fiscal_year_end_date | pass | pass | yes |
| filing_001 | gross_profit_2024_thousands | pass | pass | yes |
| filing_001 | net_income_2024_thousands | pass | pass | yes |
| form_001 | applicant_name | pass | pass | yes |
| form_001 | applicant_role | pass | pass | yes |
| form_001 | applicant_organization | pass | pass | yes |
| form_001 | project_name | pass | pass | yes |
| form_001 | project_type | pass | pass | yes |
| form_001 | application_due_date | pass | pass | yes |
| form_handwritten_001 | patient_name | pass | pass | yes |
| form_handwritten_001 | form_date | pass | pass | yes |
| form_handwritten_001 | symptoms | pass | pass | yes |
| form_handwritten_001 | instruction | pass | pass | yes |
| form_handwritten_001 | signature | pass | pass | yes |
| form_library_001 | organization_name | pass | pass | yes |
| form_library_001 | form_title | pass | pass | yes |
| form_library_001 | membership_types | pass | pass | yes |
| form_library_001 | interests_list | pass | pass | yes |
| invoice_001 | invoice_number | pass | pass | yes |
| invoice_001 | invoice_date | pass | pass | yes |
| invoice_001 | due_date | pass | pass | yes |
| invoice_001 | vendor_name | pass | pass | yes |
| invoice_001 | total_amount | pass | pass | yes |
| invoice_002 | invoice_number | pass | pass | yes |
| invoice_002 | vendor_name | pass | pass | yes |
| invoice_002 | customer_name | pass | pass | yes |
| invoice_002 | total_amount | pass | pass | yes |
| invoice_003 | supplier_name_with_id | pass | pass | yes |
| invoice_003 | buyer_name | pass | pass | yes |
| invoice_003 | invoice_date | pass | pass | yes |
| invoice_003 | due_date | pass | pass | yes |
| invoice_003 | total_amount | pass | pass | yes |
| notice_001 | notice_date | pass | pass | yes |
| notice_001 | first_affected_area | pass | pass | yes |
| notice_001 | interruption_date | pass | pass | yes |
| notice_001 | start_time | pass | pass | yes |
| notice_001 | end_time | pass | pass | yes |
| notice_001 | issuer_name | pass | pass | yes |
| receipt_001 | merchant_name | pass | pass | yes |
| receipt_001 | purchase_date | pass | pass | yes |
| receipt_001 | total_amount | pass | pass | yes |
| receipt_001 | payment_method | pass | pass | yes |
| receipt_002 | merchant_name | pass | pass | yes |
| receipt_002 | order_number | fail | pass | yes |
| receipt_002 | purchase_date | pass | pass | yes |
| receipt_002 | total_amount | pass | pass | yes |
| scan_agreement_001 | licensor_name | pass | pass | yes |
| scan_agreement_001 | licensor_address | pass | pass | yes |
| scan_agreement_001 | agreement_date | pass | pass | yes |
| scan_agreement_001 | monthly_licence_fee | pass | pass | yes |
| scan_invoice_001 | invoice_number | pass | pass | yes |
| scan_invoice_001 | invoice_date | pass | pass | yes |
| scan_invoice_001 | due_date | pass | pass | yes |
| scan_invoice_001 | total_amount | pass | pass | yes |
| scan_invoice_001 | vendor_name | pass | pass | yes |
| scan_letter_001 | issuer_name | pass | pass | yes |
| scan_letter_001 | letter_date | pass | pass | yes |
| scan_letter_001 | reference_number | pass | pass | yes |
| scan_letter_001 | new_monthly_charge | pass | pass | yes |
| scan_letter_001 | effective_date | pass | pass | yes |
| scan_notice_001 | notice_date | pass | pass | yes |
| scan_notice_001 | block_a_water_off_date | fail | pass | yes |
| scan_notice_001 | block_a_water_off_start | pass | pass | yes |
| scan_notice_001 | block_a_water_off_end | pass | pass | yes |
| scan_notice_001 | signer_name | pass | pass | yes |
| scan_report_001 | organization_name | pass | pass | yes |
| scan_report_001 | report_period | pass | pass | yes |
| scan_report_001 | days_open | pass | pass | yes |
| scan_report_001 | annual_visits | pass | pass | yes |
| scan_report_001 | printed_book_loans | pass | pass | yes |
| statement_001 | bank_name | pass | pass | yes |
| statement_001 | account_holder | pass | pass | yes |
| statement_001 | account_number | pass | pass | yes |
| statement_001 | period_start_date | pass | pass | yes |
| statement_001 | opening_balance | pass | pass | yes |
| statement_001 | closing_balance | pass | pass | yes |
| utility_001 | provider_name | pass | pass | yes |
| utility_001 | account_number | pass | pass | yes |
| utility_001 | billing_period_start | pass | pass | yes |
| utility_001 | billing_period_end | pass | pass | yes |
| utility_001 | total_due | pass | pass | yes |
| w2_001 | employer_name | pass | pass | yes |
| w2_001 | employee_name | pass | pass | yes |
| w2_001 | social_security_wages | pass | pass | yes |
| w2_001 | wages | pass | pass | yes |
| w2_001 | federal_income_tax_withheld | pass | pass | yes |


## Regression comparison

Previous: 2026-11-14T10:08:17.251438+00:00
Current: 2026-11-14T10:14:42.639954+00:00

Accuracy: +2.06 percentage points
Reference cost: $-0.000068
Mean latency: +0.053s
Cached vision documents: 5 -> 5
Regression detected: no
Added documents: none
Removed documents: none
Added fields: contract_offer_001 / candidate_name_with_id, invoice_003 / supplier_name_with_id
Removed fields: contract_offer_001 / candidate_name, invoice_003 / supplier_name

### Field changes

- invoice_003 / buyer_name (exact): fail -> pass
- invoice_003 / buyer_name (judge): fail -> pass
- scan_report_001 / report_period (exact): fail -> pass

<!-- RESULTS_END -->

## An observed extraction failure and fix

The public [three-language water notice](https://filedone.ai/sample-files/sample-notice-en-fr-es.pdf) lists three affected areas with different hours. In the first full run, a generic `affected_area` request made the model combine all three areas into one value. It also included the signer's title in `issuer_name`, and a weekday-prefixed date counted as an exact mismatch. The notice scored 3/6 exact and 5/6 grounded.

The answer values stayed the same. The request was renamed to `first_affected_area`, the instructions for choosing the first listed item and the issuing organization were clarified, and weekday-prefixed dates were normalized. The next full run scored the notice 6/6. This is a fictional public test document, so the result does not establish performance on an operational document.

## What this project does not claim

- It does not claim any model is accurate on documents in general.
- It has not been used in production or on private documents.
- Fresh OCR is slow on CPU-only hardware: about 17 minutes for eight pages.
- Everything listed under Phase 3 is a specification until the status table says otherwise.
