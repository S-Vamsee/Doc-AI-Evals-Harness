# Phase 2 human answer keys

The 15 new PDFs now have answer keys supplied by the project owner after reading the documents. The matching templates remain blank as references. Each key has 4–8 facts visibly present on its PDF. No extraction model supplied the answer values. Suggested template fields are optional: the final keys retain the facts the owner provided, including four correctly relabeled facts for the rental agreement.

For future additions, read each PDF yourself and send verified facts grouped by document ID, with a one-based page number for each fact. The values can then be formatted into JSON without an extraction model choosing them.

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

When adding or revising a key, use only facts you checked, save it without `.template` in `data/ground_truth/`, and keep the `doc_id` and `source_url` unchanged. The runner rejects keys with fewer than four or more than eight fields, missing values, invalid pages, or a mismatched source URL. The original five answer keys remain the judge's golden set.
