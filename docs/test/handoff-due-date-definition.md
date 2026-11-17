# Test-chat handoff: neutral due-date definition

Branch: `rebuild/core-rules`. This change follows the test chat's verdict on `1d0d7ac`. The only approved definition edit is `invoice_002.due_date`: “The payment-due date; excludes the invoice issue date.” Its prior wording mentioned a known empty due-date label. The answer key remains unchanged, with `due_date = null`.

All three live runs of the same public `invoice_002` page used the changed prompt hash `c93b3c46c4e6f73580e34d547fc109be02a123fbbc7924ed55ebf76a40cbece3`. They were separate model calls with no automatic retry or cache. Each run completed and returned an explicit null for `due_date`; each was scored as an abstention and an exact pass. Run IDs: `20261117T045453850664Z`, `20261117T045506367567Z`, `20261117T045517426062Z`. The full reports, manifests, results, and call logs are in the local ignored `results/environments/live-dev/pages/invoice_002/` and `results/experiments/invoice002_due_date_definition/` directories. No non-null due-date finding occurred.

The builder reviewed all 103 per-field definitions. Three other definitions contain condition-bearing “entered” wording. These are proposals only and were **not** changed:

| Field | Current wording | Proposed neutral wording |
| --- | --- | --- |
| `form_handwritten_001.form_date` | The date entered for the form; excludes unrelated dates. | The date of the patient form; excludes unrelated dates. |
| `form_handwritten_001.instruction` | The care instruction entered on the form; excludes symptoms and form descriptors. | The care instruction on the form; excludes symptoms and form descriptors. |
| `form_library_001.full_name` | A name entered in the applicant full-name field; excludes names printed elsewhere on the form. | The applicant's full name in the full-name field; excludes names printed elsewhere on the form. |

No other definition contained “entered”, “empty”, “blank”, “if present”, or another statement of a known document condition on review. Await owner approval before applying these three proposals. Day 4 has not started. The judge remains disabled.
