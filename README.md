# Document AI Evals Harness

This CLI harness scores document fact extraction against human-written answer keys. Phase 1 established a five-document text-PDF baseline; Phase 2 extends it to 20 public PDFs with scanned-page vision, a calibrated value judge, and regression comparisons. There is no web UI or database.

## Phase 1 — five text PDFs

Phase 1 used a public invoice, bank statement, W-2, SEC filing, and completed application. The owner verified 26 answer-key facts. Python read each PDF's text layer, sent the requested fields to DeepSeek, and scored exact accuracy, text groundedness, API usage, and latency. The five-document path remains available without Qwen or the Phase 2 judge:

```bash
python run_eval.py --phase1
```

This writes a separate `results/phase1/` report and timestamped run, preserving the Phase 2 results. The [original Phase 1 baseline](results/runs/20261113T113356Z/report.md) and a [fresh independent rerun](results/phase1/report.md) both scored 26/26. The rerun produced:

| Document | Fields | Exact accuracy | Groundedness |
| --- | ---: | ---: | ---: |
| Invoice | 5 | 100% | 100% |
| Bank statement | 6 | 100% | 100% |
| W-2 tax form | 5 | 100% | 100% |
| SEC filing | 4 | 100% | 100% |
| Completed application | 6 | 100% | 100% |
| **Overall** | **26** | **100%** | **100%** |

The W-2's large printed year is absent from its selectable text. The owner verified box 3 social security wages as the replacement field. These results show the base pipeline worked on five examples; they do not measure general document accuracy.

## Phase 2 — vision, judging, and regression

Phase 2 adds 15 more public PDFs and owner-verified answer keys, bringing the dataset to 20 PDFs and 97 facts. Five PDFs have no text layer; local Qwen vision transcribes those pages before DeepSeek extracts fields. A calibrated judge scores value equivalence, and timestamped runs expose field-level changes. The [latest Phase 2 results](results/report.md) and an observed document problem are below.

## Setup and commands

Clone this repository and enter its directory, then install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Create `.env` (see `.env.example`) with `DEEPSEEK_API_KEY=...`. For an OpenAI-compatible hosted deployment, also set `DEEPSEEK_BASE_URL` and `DEEPSEEK_MODEL` locally. All 20 human answer keys are in `data/ground_truth/`; the [Phase 2 guide](data/ground_truth/PHASE2_GUIDE.md) records how they were prepared.

For image-only PDFs, install [Ollama](https://docs.ollama.com/windows) locally and download the [Qwen3-VL 2B instruct model](https://ollama.com/library/qwen3-vl%3A2b-instruct):

```bash
ollama pull qwen3-vl:2b-instruct
```

Ollama serves `http://localhost:11434` by default. The harness checks that the model is installed, renders each scanned page, and asks Qwen to transcribe it before DeepSeek extracts fields. Set `QWEN_BASE_URL` and `QWEN_MODEL` in `.env` only if your local setup differs. New image-only PDFs follow the same path without document-specific code.

Run Phase 1 independently, or calibrate the judge and run Phase 2:

```bash
python run_eval.py --phase1
python run_eval.py --calibrate
python run_eval.py
python run_eval.py --reuse-ocr
python run_eval.py --compare 20261114T100817251438Z
```

`--calibrate` judges 26 fixed model candidates from the original five documents and must agree with exact scoring on at least 25. It currently agrees on 26/26. The full command checks all answer keys and scanned-PDF readiness before any paid extraction calls; if blocked, it writes `results/phase2_readiness.md`. Completed runs save per-field verdicts in timestamped `results/runs/` folders. `--reuse-ocr` reuses local Qwen transcriptions only when the PDF, installed model digest, and OCR prompt are unchanged; a normal run transcribes fresh pages. `--compare` prints field pass/fail flips, field additions/removals, and changes in accuracy, reference cost, and latency. `.env`, rendered page images, and OCR caches are ignored by Git.

## Dataset and sources

The original five text PDFs remain the golden set. The new PDFs include five image-only specimens for vision testing, plus receipts, invoices, forms, a utility bill, and short agreements. Every PDF has a public source URL in [`data/sources.json`](data/sources.json). The table below lists the Phase 1 sources:

| Local PDF | Type | Public source |
| --- | --- | --- |
| `invoice_001.pdf` | Invoice | [filedone sample](https://filedone.ai/sample-files/sample-invoice.pdf) |
| `statement_001.pdf` | Bank statement | [filedone sample](https://filedone.ai/sample-files/sample-bank-statement.pdf) |
| `w2_001.pdf` | W-2 tax form | [ePayStubs sample](https://epaystubs.net/pdfs/W2_ORD6AEC6730533E5.pdf) |
| `filing_001.pdf` | Form 10-K excerpt | [Mama's Creations FY2024 filing](https://www.annualreports.com/HostedData/AnnualReportArchive/m/NASDAQ_MAMA_2023.pdf) |
| `form_001.pdf` | Completed application | [Maryland DOT sample](https://www.mdot.maryland.gov/OPCP/06_MDOTPrioritization_SampleCompletedApplicationTOD_2025.01.15.pdf) |

## Scoring

- **Accuracy:** exact matches after normalization divided by fields in the human answer key. Dates and amounts use deterministic normalization. A calibrated value judge adds a separate per-field semantic verdict for harmless near-matches; it never changes the exact score.
- **Groundedness:** among non-null model values, the fraction found in the extracted PDF text, or in Qwen's transcription for image-only PDFs. Date display variants and currency punctuation are normalized. On scans, a mistaken Qwen transcription can affect this score, so visual spot checks remain useful.
- **Reference cost:** estimated USD from measured tokens and [published DeepSeek Flash rates](https://api-docs.deepseek.com/quick_start/pricing/). It is a benchmark estimate, not a billing record. Completed Phase 2 runs include extractor and judge calls; calibration calls are separate.
- **Latency:** wall-clock seconds spent on local vision, extraction, and judge calls, reported separately and in total. The reference cost includes API tokens; local Qwen compute has no per-token API charge.

The public results use the generic `deepseek-flash` label; the actual deployment name stays in `.env`. Extraction prompts contain PDF text and requested field names, never answer-key values. The judge sees extracted and expected values plus source text, and scores value equivalence only. Its fixed calibration candidates are in [`data/golden_candidates.json`](data/golden_candidates.json), separate from the human answer keys. The 26 golden fields all passed exact scoring, so the 26/26 calibration result alone would not test a near-match or a false positive. A separate two-case probe accepted `Acme Corp` as equivalent to `Acme Corporation` and rejected a changed amount (`200` versus `100`).

## Phase 2 results

The table below is the latest completed **20-document run**. It used cached, unchanged Qwen transcriptions to compare extraction and scoring changes, so the listed latency excludes local vision time. The [first full run](results/runs/20261114T100354369617Z/report.md) transcribed all eight scanned pages afresh; local vision took 1,016.4 seconds on this CPU-only machine. Scores describe this small public dataset and are not a general accuracy claim.

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

## Observed messy-document problem

The public [three-language water notice](https://filedone.ai/sample-files/sample-notice-en-fr-es.pdf) lists three affected areas with different hours. In the first full run, a generic `affected_area` request caused the model to combine all three areas into one value. It also included the signer's title in `issuer_name`; a weekday-prefixed date was counted as an exact mismatch. The notice scored **3/6 exact** and **5/6 grounded**.

The owner's answer values stayed the same. We renamed the request to `first_affected_area`, clarified how to select the first listed item and issuing organization, and normalized weekday-prefixed dates. A targeted check and the next full run scored the notice **6/6 exact, judge-matched, and grounded**. This is an observed extraction failure and fix on a fictional public test document; it does not establish performance on an operational document.

## Current limits

The five scans are processed by local Qwen, but fresh OCR took about 17 minutes for eight pages on this CPU-only machine. Cached regression runs are faster and report that vision time was excluded. The next evidence step is an authentic messy-document case study with a human-verified answer key. Reference API cost is estimated from usage; actual Azure billing is not measured here.
