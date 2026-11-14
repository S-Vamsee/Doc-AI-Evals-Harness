# Evaluation results

Run: 2026-11-14T10:25:28.261742+00:00

| Doc | Extractor | Fields | Exact | Grounded | Reference API cost (est.) | Latency |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| filing_001 | deepseek-flash | 4 | 100.0% | 100.0% | $0.000345 | 2.67s |
| form_001 | deepseek-flash | 6 | 100.0% | 100.0% | $0.001030 | 1.73s |
| invoice_001 | deepseek-flash | 5 | 100.0% | 100.0% | $0.000164 | 1.18s |
| statement_001 | deepseek-flash | 6 | 100.0% | 100.0% | $0.000287 | 1.18s |
| w2_001 | deepseek-flash | 5 | 100.0% | 100.0% | $0.000286 | 1.44s |
| **Overall** | — | 26 | 100.0% | 100.0% | $0.002112 total | 1.64s avg |

## Failures

None.

## Field verdicts

| Doc | Field | Exact | Grounded |
| --- | --- | --- | --- |
| filing_001 | company_name | pass | yes |
| filing_001 | fiscal_year_end_date | pass | yes |
| filing_001 | gross_profit_2024_thousands | pass | yes |
| filing_001 | net_income_2024_thousands | pass | yes |
| form_001 | applicant_name | pass | yes |
| form_001 | applicant_role | pass | yes |
| form_001 | applicant_organization | pass | yes |
| form_001 | project_name | pass | yes |
| form_001 | project_type | pass | yes |
| form_001 | application_due_date | pass | yes |
| invoice_001 | invoice_number | pass | yes |
| invoice_001 | invoice_date | pass | yes |
| invoice_001 | due_date | pass | yes |
| invoice_001 | vendor_name | pass | yes |
| invoice_001 | total_amount | pass | yes |
| statement_001 | bank_name | pass | yes |
| statement_001 | account_holder | pass | yes |
| statement_001 | account_number | pass | yes |
| statement_001 | period_start_date | pass | yes |
| statement_001 | opening_balance | pass | yes |
| statement_001 | closing_balance | pass | yes |
| w2_001 | employer_name | pass | yes |
| w2_001 | employee_name | pass | yes |
| w2_001 | social_security_wages | pass | yes |
| w2_001 | wages | pass | yes |
| w2_001 | federal_income_tax_withheld | pass | yes |
