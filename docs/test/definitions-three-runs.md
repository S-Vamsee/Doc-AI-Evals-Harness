# Approved definitions: three text-PDF runs

The keyed path is the core result. This comparison covers 15 public text PDFs, 17 pages, and 79 owner-keyed fields per run. Each keyed and open call completed. Open extraction is experimental; its counts appear below. The five scans and judge scoring are outside this measurement.

The new live calls used the approved five shared rules and 103 per-field definitions from `data/field_definitions.md`. The initial live reports scored 74, 73, and 74 fields correctly. A regression test then caught a scoring bug: an explicit null was treated as an inferred failure when the model marked its origin `inferred`. The null is an abstention and is scored against its key. The final column below is an **offline rescore of the saved live replies**, with prompt and input hashes checked; it made no new model calls and did not alter any model answer.

| Paired run | Previous live | New live, original report | New saved replies, corrected rescore | New run ID |
| --- | ---: | ---: | ---: | --- |
| 1 | 71/79 | 74/79 | **77/79** | `20261117T040618822456Z` |
| 2 | 70/79 | 73/79 | **77/79** | `20261117T040940475226Z` |
| 3 | 71/79 | 74/79 | **77/79** | `20261117T041252728554Z` |

The old run IDs were `20261115T122357120774Z`, `20261115T122632405605Z`, and `20261115T122928623104Z`, respectively. Paired exact scores improved by 6, 7, and 6 fields, with no field changing from pass to fail. The two owner-approved corrections to `form_handwritten_001` and earlier approved scorer/date changes are part of this comparison, so the gain is **not** attributable to definitions alone.

## Every changed keyed field

The table includes every distinct field whose value or pass/fail result changed between a previous run and its paired corrected replay. `R1`, `R2`, and `R3` identify the affected pairs. These are the four agreed miss kinds, including fields that improved.

| Field | Changed in | Miss kind | Reason |
| --- | --- | --- | --- |
| `contract_amendment_001.acceptance_window_days` | R1, R2 score; R3 value | Scorer gap | The earlier `fifteen` failed against `15`; the owner-approved number-word rule now treats them as the same. R3 changed from `15` to `fifteen`, with both passing. |
| `form_handwritten_001.instruction` | R1 value; R2, R3 value and score | Field or key under-defined | The old key included the specimen form descriptor. The approved key is `rest and hydrate`; R2 and R3 changed from null to that printed instruction. |
| `form_handwritten_001.signature` | R1–R3 value | Field or key under-defined | The old value and key included `(SAMPLE)`. The owner-approved key and new extraction are `J. Rivera`; both old and new passed their respective keys. |
| `form_handwritten_001.symptoms` | R1–R3 value and score | Model miss | The old extraction included the specimen marking; the new extraction is `mild headache`, matching the previously corrected key. |
| `invoice_003.buyer_name` | R1–R3 value and score | Model miss | The old extraction added `(BUY-GRP)`; the new extraction gives the owner-keyed organisation name only. |
| `notice_001.issuer_name` | R1–R3 value and score | Model miss | The old extraction included `Executive Engineer`; the new extraction gives `Sampleton Water Board`. |
| `notice_001.notice_date` | R1–R3 score | Scorer gap | The model value remained `6/10/2026`; the owner-approved DMY setting now scores its date correctly. |
| `w2_001.employee_name` | R1–R3 value and score | Model miss | The old extraction dropped `Jr.`; the new extraction includes it. |

Two keyed fields still fail in all three new runs: `receipt_002.order_number` is a **model miss** because the model drops the printed `#` prefix, and `w2_001.tax_year` is **inference correctly caught** because the model uses the year from an identifier rather than a printed tax-year field. No changed field is classified as inference correctly caught; that failure persisted.

## Fact states and open extraction

| Measure | New run 1 | New run 2 | New run 3 |
| --- | ---: | ---: | ---: |
| All facts in | 414 | 437 | 408 |
| Verified | 69 | 103 | 82 |
| Uncertain | 317 | 328 | 301 |
| Failed | 2 | 1 | 4 |
| Skipped, including abstentions | 26 | 5 | 21 |
| Open facts, experimental | 335 | 358 | 329 |
| Open verified, experimental | 51 | 85 | 64 |
| Open uncertain, experimental | 282 | 272 | 261 |
| Open failed, experimental | 2 | 1 | 4 |
| Open/keyed overlaps | 30 | 38 | 40 |

Uncertain reasons, in run order: quote occurs more than once (132/134/135); no printed role label (92/115/64); role hint absent (37/33/33); quote not found (15/12/28); typed value unsupported by quote (40/33/40); inferred value (1/1/1). The role hint is lexical and remains separate from a verified printed role label. These are counts for these runs, not a general accuracy claim.
