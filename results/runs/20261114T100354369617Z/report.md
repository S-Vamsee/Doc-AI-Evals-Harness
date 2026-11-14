# Evaluation results

Run: 2026-11-14T10:03:54.369617+00:00

| Doc | Model | Fields | Accuracy | Grounded | Reference cost (est.) | Latency |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| contract_amendment_001 | deepseek-flash | 5 | 100.0% | 100.0% | $0.000545 | 8.97s |
| contract_offer_001 | deepseek-flash | 5 | 80.0% | 100.0% | $0.000735 | 2.70s |
| filing_001 | deepseek-flash | 4 | 100.0% | 100.0% | $0.000927 | 4.31s |
| form_001 | deepseek-flash | 6 | 100.0% | 100.0% | $0.001527 | 2.98s |
| form_handwritten_001 | deepseek-flash | 5 | 100.0% | 100.0% | $0.000245 | 2.26s |
| form_library_001 | deepseek-flash | 4 | 100.0% | 100.0% | $0.000388 | 2.88s |
| invoice_001 | deepseek-flash | 5 | 100.0% | 100.0% | $0.000622 | 3.01s |
| invoice_002 | deepseek-flash | 4 | 100.0% | 100.0% | $0.000298 | 2.29s |
| invoice_003 | deepseek-flash | 5 | 80.0% | 100.0% | $0.000539 | 2.41s |
| notice_001 | deepseek-flash | 6 | 50.0% | 83.3% | $0.000682 | 2.72s |
| receipt_001 | deepseek-flash | 4 | 100.0% | 100.0% | $0.000298 | 2.20s |
| receipt_002 | deepseek-flash | 4 | 75.0% | 100.0% | $0.000241 | 3.29s |
| scan_agreement_001 | deepseek-flash | 4 | 75.0% | 100.0% | $0.000485 | 269.15s |
| scan_invoice_001 | deepseek-flash | 5 | 100.0% | 100.0% | $0.000591 | 80.59s |
| scan_letter_001 | deepseek-flash | 5 | 100.0% | 100.0% | $0.000481 | 138.58s |
| scan_notice_001 | deepseek-flash | 5 | 80.0% | 100.0% | $0.000588 | 144.84s |
| scan_report_001 | deepseek-flash | 5 | 80.0% | 80.0% | $0.000578 | 397.67s |
| statement_001 | deepseek-flash | 6 | 100.0% | 100.0% | $0.001102 | 2.88s |
| utility_001 | deepseek-flash | 5 | 100.0% | 100.0% | $0.000347 | 2.56s |
| w2_001 | deepseek-flash | 5 | 100.0% | 100.0% | $0.000585 | 2.76s |
| **Overall** | — | 97 | 90.7% | 97.9% | $0.011802 total | 53.95s avg |

## Failures

- **contract_offer_001 / candidate_name**: expected `Team member 5 (EMP-05)`, got `Team member 5`
- **invoice_003 / supplier_name**: expected `Harbour Food Supply (SUP-02)`, got `Harbour Food Supply`
- **notice_001 / affected_area**: expected `Market Road and Station Lane`, got `Market Road and Station Lane, Hill View Colony, River Side blocks 1 to 4`
- **notice_001 / interruption_date**: expected `Tuesday 13 October 2026`, got `2026-10-13`
- **notice_001 / issuer_name**: expected `Sampleton Water Board`, got `Executive Engineer, Sampleton Water Board`
- **notice_001 / affected_area**: `Market Road and Station Lane, Hill View Colony, River Side blocks 1 to 4` was not found in the extracted PDF text
- **receipt_002 / order_number**: expected `#NV-10482`, got `NV-10482`
- **scan_agreement_001 / agreement_date**: expected `25th day of September 2026`, got `2026-09-25`
- **scan_notice_001 / block_a_water_off_date**: expected `Mon 12 Oct`, got `2026-10-12`
- **scan_report_001 / report_period**: expected `April 2025 to March 2026`, got `2025-04 to 2026-03`
- **scan_report_001 / report_period**: `2025-04 to 2026-03` was not found in the extracted PDF text

## Field verdicts

| Doc | Field | Exact | Judge | Grounded |
| --- | --- | --- | --- | --- |
| contract_amendment_001 | amendment_reference | pass | pass | yes |
| contract_amendment_001 | effective_date | pass | pass | yes |
| contract_amendment_001 | old_expense_cap | pass | pass | yes |
| contract_amendment_001 | new_expense_cap | pass | pass | yes |
| contract_amendment_001 | acceptance_window_days | pass | pass | yes |
| contract_offer_001 | employer_name | pass | pass | yes |
| contract_offer_001 | candidate_name | fail | fail | yes |
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
| invoice_003 | supplier_name | fail | fail | yes |
| invoice_003 | buyer_name | pass | pass | yes |
| invoice_003 | invoice_date | pass | pass | yes |
| invoice_003 | due_date | pass | pass | yes |
| invoice_003 | total_amount | pass | pass | yes |
| notice_001 | notice_date | pass | pass | yes |
| notice_001 | affected_area | fail | fail | no |
| notice_001 | interruption_date | fail | pass | yes |
| notice_001 | start_time | pass | pass | yes |
| notice_001 | end_time | pass | pass | yes |
| notice_001 | issuer_name | fail | fail | yes |
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
| scan_agreement_001 | agreement_date | fail | pass | yes |
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
| scan_report_001 | report_period | fail | pass | no |
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

Previous: 2026-11-13T11:33:56+00:00
Current: 2026-11-14T10:03:54.369617+00:00

Accuracy: -9.28 percentage points
Reference cost: $+0.009733
Mean latency: +50.806s
Regression detected: yes
Added documents: contract_amendment_001, contract_offer_001, form_handwritten_001, form_library_001, invoice_002, invoice_003, notice_001, receipt_001, receipt_002, scan_agreement_001, scan_invoice_001, scan_letter_001, scan_notice_001, scan_report_001, utility_001
Removed documents: none

### Field changes

No pass/fail changes among fields scored in both runs.
