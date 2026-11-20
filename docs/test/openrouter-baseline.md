# New baseline on OpenRouter — text PDFs, three runs

Date: 2026-11-19. Environment: `live-dev`. Model: `deepseek/deepseek-v4-flash-0731` through
OpenRouter, hidden reasoning off. Run IDs `20261120T064751993704Z`, `20261120T065055201905Z`,
`20261120T065407738744Z`.

What was tested, and why: the model provider changed, so earlier scores cannot be compared
directly. This sets a new baseline on the same 15 text PDFs and 79 owner-keyed fields.

Command: `C:\venvs\harness\Scripts\python.exe scripts\environments.py live-dev -- --development --text-only`

| Measure | Run 1 | Run 2 | Run 3 |
| --- | ---: | ---: | ---: |
| Keyed fields correct | 73/79 | 77/79 | 77/79 |
| Complete pages | 15/17 | 16/17 | 16/17 |
| Facts verified / uncertain / failed | 97 / 313 / 0 | 82 / 327 / 2 | 92 / 341 / 0 |
| Cost reported by OpenRouter | $0.00994 | $0.00934 | $0.00933 |

Keyed misses:

- `receipt_002.order_number`, every run: model miss, the printed `#` is dropped.
- `w2_001.tax_year`, every run: inference correctly caught, the year comes from an identifier.
- `receipt_001`, run 1 only, four fields: the keyed reply added a field named `origin` beside
  the requested ones, so the whole reply was rejected as an extraction failure.

Other failures, open-facts request (experimental): two empty replies for
`form_handwritten_001`, and two facts in `w2_001` given a kind outside the allowed list.

What this does not prove: accuracy on unseen documents; the same tuning caveat as Day 3 applies.
Runs 2 and 3 match the last Azure baseline (77/79 with the same two misses), but the two
models are different, so this is not a like-for-like comparison.

Cost: $0.0286 for all three runs as reported by OpenRouter. The older reference estimate
said $0.137, about five times too high, because it uses DeepSeek's own published rates.
