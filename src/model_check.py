"""One small request that shows whether the configured model can be reached."""

from __future__ import annotations

import json
import sys

from src import core_pipeline
from src.model_config import endpoint_summary, public_model_label


CHECK_MESSAGES = [
    {"role": "system", "content": "Return JSON only."},
    {"role": "user", "content": 'Return exactly this JSON object: {"ok": true}'},
]


def check_model(model_request=None, out=None) -> int:
    """Print what answered and what it cost; exit 0 only on a correct reply."""
    out = out or sys.stdout
    endpoint = endpoint_summary()
    print(f"Provider: {endpoint['provider']} ({endpoint['provider_host']}); "
          f"model label: {public_model_label()}", file=out)
    try:
        reply = (model_request or (lambda m: core_pipeline._live_request(m, max_tokens=20)))(
            CHECK_MESSAGES)
    except Exception as exc:
        print(f"Failed: {type(exc).__name__}: {exc}", file=out)
        return 1
    try:
        ok = json.loads(reply["content"]).get("ok") is True
    except (ValueError, AttributeError):
        ok = False
    usage = reply.get("usage") or {}
    cost = reply.get("cost_usd")
    print(f"Reply: {reply['content'].strip()[:80]}", file=out)
    print(f"Tokens in/out: {usage.get('prompt_tokens')}/{usage.get('completion_tokens')}; "
          f"time: {reply.get('latency_seconds')}s; provider-reported cost: "
          + (f"${cost:.6f}" if cost is not None else "not reported"), file=out)
    print("Connection works." if ok else "The model answered, but not with the expected JSON.",
          file=out)
    return 0 if ok else 1
