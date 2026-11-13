# Document AI Evals Harness — Phase 1

This CLI harness extracts facts from five public, text-based PDFs with one DeepSeek model and scores the results against human-written answer keys. One command writes per-document JSON, a Markdown results table, and aggregate accuracy, groundedness, cost, and latency.

## Run

Clone this repository and enter its directory, then install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Create `.env` (see `.env.example`) with `DEEPSEEK_API_KEY=...`. For an OpenAI-compatible hosted deployment, also set `DEEPSEEK_BASE_URL` and `DEEPSEEK_MODEL` to its endpoint and deployment name. Read the five PDFs and write the matching JSON answer keys in `data/ground_truth/` using [the format guide](data/ground_truth/README.md). Then run:

```bash
python run_eval.py
```

The command continues after a document error and exits nonzero unless all five succeed. It saves raw model text and parsed JSON in `results/extracted/`, scores in `results/scores.json`, and the table in `results/report.md`. When all five succeed, it copies the real report into this README. `.env` is ignored by Git; review the generated results before committing them.

## Dataset

Every file has a selectable text layer; no OCR is used. The invoice and statement are fictional CC0 specimens. The W-2 is a fictional sample, the filing is a two-page excerpt of a public Form 10-K, and the application is a public sample completed Maryland DOT form. The W-2's large printed year is not in its selectable text, so the text-only evaluation uses box 3 social security wages instead. See `data/sources.json` for provenance and excerpt page mapping.

| Local PDF | Type | Public source |
| --- | --- | --- |
| `invoice_001.pdf` | Invoice | [filedone sample](https://filedone.ai/sample-files/sample-invoice.pdf) |
| `statement_001.pdf` | Bank statement | [filedone sample](https://filedone.ai/sample-files/sample-bank-statement.pdf) |
| `w2_001.pdf` | W-2 tax form | [ePayStubs sample](https://epaystubs.net/pdfs/W2_ORD6AEC6730533E5.pdf) |
| `filing_001.pdf` | Form 10-K excerpt | [Mama's Creations FY2024 filing](https://www.annualreports.com/HostedData/AnnualReportArchive/m/NASDAQ_MAMA_2023.pdf) |
| `form_001.pdf` | Completed application | [Maryland DOT sample](https://www.mdot.maryland.gov/OPCP/06_MDOTPrioritization_SampleCompletedApplicationTOD_2025.01.15.pdf) |

## Scoring

- **Accuracy:** correct fields divided by all fields in the human answer key. Strings are trimmed and case-folded; dates are converted to ISO; amounts are compared as decimal numbers. No fuzzy or judge-model scoring.
- **Groundedness:** among non-null model values, the fraction found in the extracted PDF text. Date display variants and currency punctuation are normalized. This checks whether text supports a value, but it does not prove the value belongs to the right label; the accuracy score handles that separately.
- **Reference cost:** estimated USD from prompt cache-hit and cache-miss tokens and output tokens, using [DeepSeek's published direct Flash rates](https://api-docs.deepseek.com/quick_start/pricing/) checked 2026-11-13. Off-peak per million: $0.003 hit, $0.15 miss, $0.60 output. Peak per million: $0.006 hit, $0.30 miss, $1.20 output. Peak is 01:00–04:00 and 06:00–10:00 UTC on weekdays, excluding Chinese public holidays. This run uses an Azure-hosted DeepSeek deployment, so its billed price may differ; these figures are a reproducible direct-API rate comparison, not an Azure invoice.
- **Latency:** wall-clock seconds spent on the API call.

The default model is `deepseek-flash` on DeepSeek's own API, with thinking disabled, `temperature=0`, and JSON output mode. This run uses an Azure-hosted DeepSeek deployment configured locally in `.env`; public results use the generic `deepseek-flash` label. The Azure endpoint does not accept the DeepSeek-specific thinking switch, so the harness omits that parameter there. The spec's `deepseek-chat` name was [retired in July 2026](https://api-docs.deepseek.com/news/news260424/). Each prompt contains the PDF text and requested field names, never the answer-key values.

## Results

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

## Next phase

Expand to 20–30 documents, add LLM-as-judge scoring, OCR/vision for scans, and prompt regression runs. This phase stays CLI-only and has no database or web UI.
