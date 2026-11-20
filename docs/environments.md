# Test environments

Use Python 3.11. The entry point is `scripts/environments.py`. Runtime packages stay
in `requirements.txt`; pytest stays in `requirements-dev.txt`. The local virtual
environment used for development is `C:\venvs\harness`, outside OneDrive.

| Environment | Command from repo root | Purpose and allowed access | Output |
| --- | --- | --- | --- |
| `offline` | `C:\venvs\harness\Scripts\python.exe scripts\environments.py offline` | Runs all rule and replay tests. The child has no API keys, ignores `.env`, and blocks socket connections and DNS. No model calls. | Pytest output; test temporary files only. |
| `clean` | `C:\venvs\harness\Scripts\python.exe scripts\environments.py clean` | Makes a fresh virtual environment under `C:\venvs`, installs `requirements.txt` then `requirements-dev.txt` without network, runs `run_eval.py --help`, then the full offline suite. No model calls. | Fresh venv under `C:\venvs`; test temporary files only. |
| `live-dev` | `C:\venvs\harness\Scripts\python.exe scripts\environments.py live-dev -- --development` | Real hosted extractor calls on the 20 development PDFs; reads ignored `.env` and signed local scan caches. Never use held-back PDFs here. Judge scoring remains disabled. | `results/environments/live-dev/` only. |
| `live-heldback` | `C:\venvs\harness\Scripts\python.exe scripts\environments.py live-heldback -- --core-page DOC_ID:1` | Real calls only after `data/heldback/freeze.json` contains a frozen input fingerprint. Do not run before Day 9. Never tune from its results. | `results/environments/live-heldback/` only. |
| `ci` | `python scripts/environments.py ci` | The same key-free, network-blocked pytest suite on GitHub Actions. No model calls. | CI logs and test temporary files only. |

Before running `clean`, prepare the local wheelhouse once from an environment with
package-index access:

```powershell
C:\venvs\harness\Scripts\python.exe -m pip download -r requirements-dev.txt -d C:\venvs\harness-wheels
```

The `clean` command uses `--no-index` and `PIP_NO_INDEX=1` for both installations.
The clean and offline test processes prepend `scripts/offline_guard` to `PYTHONPATH`.
Its `sitecustomize.py` refuses socket connections, UDP sends, and DNS before test
code can use them. A test verifies this with a fake API key present. The guard is a
Python-process control, not a machine-wide firewall.

The live entry points require explicit `run_eval.py` arguments. The held-back entry
point refuses to start without a freeze file. The separate result roots keep their
OCR and extraction caches apart. New one-page manifests record `environment`, model
label, prompt and input hashes, code version, and cache use. Recorded injection
responses are checked against their request hash before replay. The existing legacy
full-run path still invokes the judge and is not an approved Day 1 live command.

The owner approved the 20-document judge-free development runner for Day 1. Its
cached scan facts stay uncertain until independent OCR is wired in. The held-back
command is blocked until the owner freezes that set on Day 8.

## Trying a new document

`C:\venvs\harness\Scripts\python.exe scripts\environments.py live-dev -- --tryout path\to\file.pdf`
runs a text PDF with no answer key. The page text is sent to the hosted model, so use public
documents only. Results stay in `results/tryouts/`, apart from development and held-back runs.
Exit codes: 0 complete, 1 incomplete, 2 refused.

## Model endpoint

The extraction model is set in `.env` with `HARNESS_MODEL_BASE_URL`, `HARNESS_MODEL_API_KEY`
and `HARNESS_MODEL`. Any OpenAI-compatible endpoint works; see `.env.example`. The older
`DEEPSEEK_*` names are still read when the new ones are absent.

Check the connection with one small request before any run:

`C:\venvs\harness\Scripts\python.exe scripts\environments.py live-dev -- --check-model`

Each run's manifest records the provider and host. On OpenRouter, the provider-reported
cost is saved beside the reference estimate. Changing provider or model can change answers,
so a new baseline needs three runs.
