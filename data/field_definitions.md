# Approved keyed-field definitions

Owner approved this version on 2026-11-16. This is the single source for the shared extraction rules and keyed-field definitions.

## Shared rules for every field

1. Return null when the field value is not printed.
2. Never derive a field value from another value or from an identifier.
3. Copy identifiers and currency markers exactly as printed; add none.
4. Return dates as printed.
5. Leave out specimen or sample markings.

## `contract_amendment_001`

- `amendment_reference` — The amendment's own reference identifier; excludes identifiers for other agreements or work orders.
- `effective_date` — The date the amendment takes effect; excludes the signing date.
- `old_expense_cap` — The expense cap before the amendment; excludes the replacement cap.
- `new_expense_cap` — The replacement expense cap; excludes the previous cap.
- `acceptance_window_days` — The revised endpoint of the acceptance window in business days; excludes the former endpoint.

## `contract_offer_001`

- `employer_name` — The organization making the offer; excludes the candidate and staff titles.
- `candidate_name_with_id` — The candidate name together with its attached candidate identifier; excludes the employer.
- `start_date` — The proposed employment start date; excludes the offer-expiry date.
- `hourly_rate` — The pay rate per hour; excludes annual or monthly pay.
- `offer_expiry_date` — The date the offer expires; excludes the employment start date.

## `filing_001`

- `company_name` — The filing company's legal name; excludes companies mentioned as customers or partners.
- `fiscal_year_end_date` — The fiscal year-end date; excludes filing and publication dates.
- `gross_profit_2024_thousands` — Gross profit in the target fiscal-year column at the table's stated scale; excludes sales and net income.
- `net_income_2024_thousands` — Net income in the target fiscal-year column at the table's stated scale; excludes gross profit and sales.

## `form_001`

- `applicant_name` — The person applying; excludes that person's role and organization.
- `applicant_role` — The applicant's job title or role; excludes their name and organization.
- `applicant_organization` — The organization represented by the applicant; excludes the person's name and title.
- `project_name` — The proposed project's title; excludes its category.
- `project_type` — The project's stated category; excludes its title and unselected form choices.
- `application_due_date` — The submission deadline; excludes the form-preparation date.

## `form_handwritten_001`

- `patient_name` — The patient named on the form; excludes the signer if different.
- `form_date` — The date entered for the form; excludes unrelated dates.
- `symptoms` — The patient's symptom description; excludes instructions and form annotations.
- `instruction` — The care instruction entered on the form; excludes symptoms and form descriptors.
- `signature` — The signer's written mark or name in the signature field; excludes printed form labels.

## `form_library_001`

- `organization_name` — The library named on the form; excludes an applicant's name.
- `form_title` — The title of the form; excludes section headings.
- `membership_types` — The membership categories offered, including their eligibility qualifiers; excludes an applicant's selection.
- `interests_list` — The interest categories offered as choices; excludes an applicant's selected interests.
- `full_name` — A name entered in the applicant full-name field; excludes names printed elsewhere on the form.

## `invoice_001`

- `invoice_number` — This invoice's identifier; excludes order and account identifiers.
- `invoice_date` — The issue date of this invoice; excludes its due date.
- `due_date` — The payment-due date; excludes the invoice issue date.
- `vendor_name` — The organization issuing the invoice; excludes the billed customer.
- `total_amount` — The final invoice total due; excludes subtotals and line amounts.

## `invoice_002`

- `invoice_number` — This invoice's identifier; excludes order and account identifiers.
- `vendor_name` — The seller or issuer; excludes the billed customer.
- `customer_name` — The buyer or billed organization; excludes the seller.
- `total_amount` — The final invoice total; excludes item amounts and subtotals.
- `due_date` — The payment-due date; excludes the invoice issue date.

## `invoice_003`

- `supplier_name_with_id` — The supplier's name together with its attached supplier identifier; excludes the buyer.
- `buyer_name` — The buying organization's name alone; excludes its attached buyer identifier and the supplier.
- `invoice_date` — The date this invoice was issued; excludes its due date.
- `due_date` — The payment-due date for this invoice; excludes its issue date.
- `total_amount` — The final invoice amount; excludes line amounts and subtotals.

## `notice_001`

- `notice_date` — The date the notice was issued; excludes interruption dates.
- `first_affected_area` — The first named area affected by the interruption; excludes later affected areas.
- `interruption_date` — The interruption date for the first affected area; excludes the notice date and other areas' dates.
- `start_time` — The start of the first affected area's interruption; excludes other areas' times.
- `end_time` — The end of the first affected area's interruption; excludes other areas' times.
- `issuer_name` — The organization issuing the notice; excludes the signer's job title.

## `receipt_001`

- `merchant_name` — The seller named on the receipt; excludes the customer and payment provider.
- `purchase_date` — The date of the purchase; excludes a later settlement date.
- `total_amount` — The final receipt total; excludes individual item amounts.
- `payment_method` — The tender method used for the purchase; excludes payment-account details.

## `receipt_002`

- `merchant_name` — The seller named on the receipt; excludes the customer.
- `order_number` — This purchase's order identifier; excludes receipt and account identifiers.
- `purchase_date` — The purchase date; excludes a settlement date.
- `total_amount` — The final receipt total; excludes individual item amounts.
- `customer_name` — A customer named for this purchase; excludes the merchant and payment provider.

## `scan_agreement_001`

- `licensor_name` — The person identified as licensor; excludes the licensee and witnesses.
- `licensor_address` — The licensor's address; excludes the licensed premises and licensee's address.
- `agreement_date` — The date the agreement was executed; excludes the licence start date.
- `monthly_licence_fee` — The recurring licence fee per month; excludes deposits and one-time charges.

## `scan_invoice_001`

- `invoice_number` — This invoice's identifier; excludes order and account identifiers.
- `invoice_date` — The issue date of this invoice; excludes its due date.
- `due_date` — The payment-due date; excludes the invoice issue date.
- `total_amount` — The final amount due on the invoice; excludes line amounts and subtotals.
- `vendor_name` — The organization issuing the invoice; excludes the billed party.

## `scan_letter_001`

- `issuer_name` — The organization sending the letter; excludes its recipient.
- `letter_date` — The date of the letter; excludes the charge's effective date.
- `reference_number` — This letter's reference identifier; excludes account identifiers.
- `new_monthly_charge` — The revised recurring monthly charge; excludes the previous charge.
- `effective_date` — The date the revised charge begins; excludes the letter date.

## `scan_notice_001`

- `notice_date` — The date the notice was issued; excludes scheduled water-off dates.
- `block_a_water_off_date` — The date of Block A's water-off event; excludes dates for other blocks.
- `block_a_water_off_start` — The start time of Block A's water-off interval; excludes other blocks' times.
- `block_a_water_off_end` — The end time of Block A's water-off interval; excludes other blocks' times.
- `signer_name` — The person signing the notice; excludes the issuing association and titles.

## `scan_report_001`

- `organization_name` — The organization issuing the report; excludes referenced partners.
- `report_period` — The period covered by the report; excludes its publication date.
- `days_open` — The number of days open during the report period; excludes visits and loans.
- `annual_visits` — The total visits reported for the period; excludes loans and other activity counts.
- `printed_book_loans` — The printed-book loan count for the period; excludes digital loans and visits.

## `statement_001`

- `bank_name` — The institution issuing the statement; excludes the account holder.
- `account_holder` — The named owner of the account; excludes the issuing bank.
- `account_number` — This statement's account identifier; excludes routing and transaction identifiers.
- `period_start_date` — The opening date of the statement period; excludes transaction dates.
- `opening_balance` — The balance at the beginning of the period; excludes transactions and closing balance.
- `closing_balance` — The balance at the end of the period; excludes transactions and opening balance.
- `routing_number` — A routing identifier for this bank account; excludes the account number.

## `utility_001`

- `provider_name` — The utility provider issuing the bill; excludes the account holder.
- `account_number` — This utility account's identifier; excludes meter and bill identifiers.
- `billing_period_start` — The first date of the billed service period; excludes the bill date.
- `billing_period_end` — The last date of the billed service period; excludes payment dates.
- `total_due` — The final amount payable on the bill; excludes usage figures and line charges.
- `meter_serial_number` — The physical meter's serial identifier; excludes the utility account number.

## `w2_001`

- `employer_name` — The employer's legal name; excludes the employee and payroll provider.
- `employee_name` — The employee's complete name; excludes the employer and other people.
- `tax_year` — The tax year stated for the form; excludes other dates and years.
- `social_security_wages` — The amount in the Social Security wages box; excludes other wage and tax boxes.
- `wages` — The amount in the general wages box; excludes Social Security and Medicare wage boxes.
- `federal_income_tax_withheld` — The amount in the federal income-tax-withheld box; excludes other withholding boxes.
