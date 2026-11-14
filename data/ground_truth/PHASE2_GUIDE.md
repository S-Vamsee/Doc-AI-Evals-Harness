# Phase 2 human answer keys

The 15 new PDFs are ready. Their answer keys are intentionally blank. Read each PDF yourself, select 4–8 facts visibly present on its pages, and write `data/ground_truth/<doc_id>.json` from the matching template. Do not copy a publisher's answer key or ask an extraction model to produce the values. Suggested field names in templates are optional: remove or rename any field that is not plainly visible. Use the exact printed value and a one-based page number.

You can also send your verified facts in chat, grouped by document ID with the page number for each fact, as you did for Phase 1. I will format your facts into the JSON files without choosing answer values for you.

| Document | Type | Template |
| --- | --- | --- |
| [scan_notice_001.pdf](../pdfs/scan_notice_001.pdf) | image-only notice | [template](templates/scan_notice_001.template.json) |
| [scan_report_001.pdf](../pdfs/scan_report_001.pdf) | image-only three-page report | [template](templates/scan_report_001.template.json) |
| [scan_letter_001.pdf](../pdfs/scan_letter_001.pdf) | image-only letter | [template](templates/scan_letter_001.template.json) |
| [scan_invoice_001.pdf](../pdfs/scan_invoice_001.pdf) | image-only invoice | [template](templates/scan_invoice_001.template.json) |
| [receipt_001.pdf](../pdfs/receipt_001.pdf) | receipt | [template](templates/receipt_001.template.json) |
| [form_library_001.pdf](../pdfs/form_library_001.pdf) | library application form | [template](templates/form_library_001.template.json) |
| [notice_001.pdf](../pdfs/notice_001.pdf) | three-language notice | [template](templates/notice_001.template.json) |
| [scan_agreement_001.pdf](../pdfs/scan_agreement_001.pdf) | image-only agreement | [template](templates/scan_agreement_001.template.json) |
| [invoice_002.pdf](../pdfs/invoice_002.pdf) | invoice | [template](templates/invoice_002.template.json) |
| [receipt_002.pdf](../pdfs/receipt_002.pdf) | receipt | [template](templates/receipt_002.template.json) |
| [utility_001.pdf](../pdfs/utility_001.pdf) | utility bill | [template](templates/utility_001.template.json) |
| [form_handwritten_001.pdf](../pdfs/form_handwritten_001.pdf) | handwritten-style form | [template](templates/form_handwritten_001.template.json) |
| [contract_offer_001.pdf](../pdfs/contract_offer_001.pdf) | employment offer | [template](templates/contract_offer_001.template.json) |
| [contract_amendment_001.pdf](../pdfs/contract_amendment_001.pdf) | agreement amendment | [template](templates/contract_amendment_001.template.json) |
| [invoice_003.pdf](../pdfs/invoice_003.pdf) | supplier invoice | [template](templates/invoice_003.template.json) |

For each template, replace every `null` with the fact you checked and its page number, then save it without `.template` in `data/ground_truth/`. Keep the `doc_id` and `source_url` unchanged. The runner rejects keys with fewer than four or more than eight fields, missing values, invalid pages, or a mismatched source URL. The original five answer keys remain the judge's golden set.
