# Human answer keys needed

Read each PDF in `../pdfs/` and write one JSON file here with the same base name. Do not copy facts from a model output or an online answer key. The human reviewer chooses 4–8 facts that are visible in the PDF, records their page numbers, and checks the final JSON.

Ready-to-fill files are in `templates/`. For each one, replace every `null` value and page with the facts you personally verify, adjust the field list if needed, and save the result in this directory as `<doc_id>.json` (remove `.template` from the filename). Template files are never used by the runner.

Example shape (illustrative values only; do not use as an answer key):

```json
{
  "doc_id": "invoice_001",
  "source_url": "https://filedone.ai/sample-files/sample-invoice.pdf",
  "fields": [
    {"field": "invoice_number", "value": "READ_FROM_PDF", "page": 1},
    {"field": "invoice_date", "value": "YYYY-MM-DD", "page": 1},
    {"field": "vendor_name", "value": "READ_FROM_PDF", "page": 1},
    {"field": "total_amount", "value": 0, "page": 1}
  ]
}
```

Use the source URL in `../sources.json`. Dates go in ISO form and amounts as JSON numbers without symbols or commas. Page numbers are one-based and refer to the **local PDF**. The filing is a two-page excerpt; its page 2 came from page 36 of the source PDF.

Suggested field names (choose only facts you can verify):

- `invoice_001`: `invoice_number`, `invoice_date`, `due_date`, `vendor_name`, `customer_name`, `subtotal_amount`, `total_amount`
- `statement_001`: `bank_name`, `account_holder`, `account_number`, `period_start_date`, `period_end_date`, `opening_balance`, `closing_balance`
- `w2_001`: `employer_name`, `employee_name`, `social_security_wages`, `wages`, `federal_income_tax_withheld`
- `filing_001`: `company_name`, `fiscal_year_end_date`, `net_sales_2024_thousands`, `gross_profit_2024_thousands`, `net_income_2024_thousands`
- `form_001`: select the sample applicant/project facts printed in the red response text, such as `project_name`, `project_type`, `applicant_organization`, and any dates or amounts shown.

The runner rejects missing, null, or malformed answer keys. This is intentional: it prevents a model from silently becoming its own judge.
