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
