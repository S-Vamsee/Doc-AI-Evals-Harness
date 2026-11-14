# Document AI Evals Harness — Phase 2 in progress

This CLI harness scores document fact extraction against human-written answer keys. The five text-PDF golden documents have a completed run. The dataset now contains 20 public PDFs, including five image-only PDFs; the 15 new answer keys and a Qwen vision setup are still needed before the 20-document run can start. [Read the current blockers](results/phase2_readiness.md).

## Run

Clone this repository and enter its directory, then install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Create `.env` (see `.env.example`) with `DEEPSEEK_API_KEY=...`. For an OpenAI-compatible hosted deployment, also set `DEEPSEEK_BASE_URL` and `DEEPSEEK_MODEL` locally. The original five human answer keys are already in `data/ground_truth/`. Read each new PDF and write its answer key using the [Phase 2 guide](data/ground_truth/PHASE2_GUIDE.md). Calibrate the value judge before a full run:

```bash
python run_eval.py --calibrate
python run_eval.py
python run_eval.py --compare 20261113T113356Z
```

`--calibrate` judges the 26 original fields and must agree with exact scoring on at least 25. It currently agrees on 26/26. The full command checks all answer keys and scanned-PDF readiness before any paid extraction calls; if blocked, it writes `results/phase2_readiness.md`. Completed runs save per-field verdicts in timestamped `results/runs/` folders. `--compare` prints field pass/fail flips and changes in accuracy, reference cost, and latency. `.env` and rendered page images are ignored by Git.

## Dataset

The original five text PDFs remain the golden set. The new PDFs include five image-only specimens for vision testing, plus receipts, invoices, forms, a utility bill, and short agreements. Every PDF has a public source URL in [`data/sources.json`](data/sources.json). The W-2's large printed year is absent from its selectable text, so the text-only golden key uses box 3 social security wages.

| Local PDF | Type | Public source |
| --- | --- | --- |
| `invoice_001.pdf` | Invoice | [filedone sample](https://filedone.ai/sample-files/sample-invoice.pdf) |
| `statement_001.pdf` | Bank statement | [filedone sample](https://filedone.ai/sample-files/sample-bank-statement.pdf) |
| `w2_001.pdf` | W-2 tax form | [ePayStubs sample](https://epaystubs.net/pdfs/W2_ORD6AEC6730533E5.pdf) |
| `filing_001.pdf` | Form 10-K excerpt | [Mama's Creations FY2024 filing](https://www.annualreports.com/HostedData/AnnualReportArchive/m/NASDAQ_MAMA_2023.pdf) |
| `form_001.pdf` | Completed application | [Maryland DOT sample](https://www.mdot.maryland.gov/OPCP/06_MDOTPrioritization_SampleCompletedApplicationTOD_2025.01.15.pdf) |

## Scoring

- **Accuracy:** exact matches after normalization divided by fields in the human answer key. Dates and amounts use deterministic normalization. A calibrated value judge adds a separate per-field semantic verdict for harmless near-matches; it never changes the exact score.
- **Groundedness:** among non-null model values, the fraction found in the extracted PDF text. Date display variants and currency punctuation are normalized. This checks whether text supports a value, but it does not prove the value belongs to the right label; the accuracy score handles that separately.
- **Reference cost:** estimated USD from measured tokens and [published DeepSeek Flash rates](https://api-docs.deepseek.com/quick_start/pricing/). It is a benchmark estimate, not a billing record. Completed Phase 2 runs include extractor and judge calls; calibration calls are separate.
- **Latency:** wall-clock seconds spent on extraction and judge API calls, reported separately and in total.

The public results use the generic `deepseek-flash` label; the actual deployment name stays in `.env`. Extraction prompts contain PDF text and requested field names, never answer-key values. The judge sees extracted and expected values plus source text, and scores value equivalence only. The 26 golden fields all passed exact scoring, so the 26/26 calibration result alone would not test a near-match or a false positive. A separate two-case probe accepted `Acme Corp` as equivalent to `Acme Corporation` and rejected a changed amount (`200` versus `100`).

## Results

The table below is the last completed **five-document golden-set run**, before the new documents and judge were added. It must not be read as a 20-document Phase 2 score.

<!-- RESULTS_START -->

# Evaluation results

Run: 2026-11-13T11:33:56+00:00

| Doc | Model | Fields | Accuracy | Grounded | Reference cost (est.) | Latency |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| filing_001 | deepseek-flash | 4 | 100.0% | 100.0% | $0.000336 | 4.97s |
| form_001 | deepseek-flash | 6 | 100.0% | 100.0% | $0.001022 | 2.34s |
| invoice_001 | deepseek-flash | 5 | 100.0% | 100.0% | $0.000155 | 2.76s |
| statement_001 | deepseek-flash | 6 | 100.0% | 100.0% | $0.000279 | 3.02s |
| w2_001 | deepseek-flash | 5 | 100.0% | 100.0% | $0.000277 | 2.64s |
| **Overall** | — | 26 | 100.0% | 100.0% | $0.002069 total | 3.15s avg |

## Failures

None.

<!-- RESULTS_END -->

## Current Phase 2 blockers

The 15 new human answer keys are pending. Five image-only PDFs need a configured Qwen vision service; no local service is currently available, and the harness does not substitute another model. A public messy-document case study will be written only after a real extraction run shows a concrete problem and fix. See the [readiness report](results/phase2_readiness.md).
