"""Value-equivalence judge for human-verified document facts."""

from __future__ import annotations

import json
import os
import time

from openai import OpenAI

from src.score import estimated_cost


def judge_document(extracted: dict, truth: dict, pages: list[str]) -> dict:
    """Judge value equivalence only; groundedness remains deterministic."""
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is required for judge calibration")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    candidates = {item["field"]: item for item in extracted["fields"]}
    inputs = [
        {
            "field": item["field"],
            "expected": item["value"],
            "extracted": candidates[item["field"]]["value"],
            "source_text": pages[item["page"] - 1][:8000],
        }
        for item in truth["fields"]
    ]
    system = (
        "You compare extracted document values against human-verified reference values. "
        "For each field, decide whether the extracted value means the same thing as the "
        "reference. Accept harmless abbreviation, punctuation, spacing, and name suffix "
        "formatting differences. A missing name suffix is a mismatch. Reject missing values, different people or organizations, "
        "different numbers, different dates, or values that change the meaning. "
        "The source text is context only; do not assess whether the value is grounded. "
        'Return only JSON: {"verdicts":[{"field":"...","match":true,"reason":"..."}]}.'
    )
    client = OpenAI(api_key=key, base_url=base_url, timeout=120.0)
    started = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(inputs, ensure_ascii=False)},
        ],
        temperature=0,
        response_format={"type": "json_object"},
        max_tokens=1400,
    )
    latency = time.perf_counter() - started
    raw = response.choices[0].message.content or ""
    parsed = json.loads(raw)
    verdicts = parsed.get("verdicts")
    names = [item["field"] for item in truth["fields"]]
    if not isinstance(verdicts, list) or [item.get("field") for item in verdicts] != names:
        raise ValueError("Judge returned a mismatched field list")
    for item in verdicts:
        if not isinstance(item.get("match"), bool) or not isinstance(item.get("reason"), str):
            raise ValueError("Judge returned an invalid verdict")
    usage = response.usage
    if usage is None:
        raise ValueError("Judge response did not include token usage")
    token_usage = {
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "prompt_cache_hit_tokens": getattr(usage, "prompt_cache_hit_tokens", 0),
        "prompt_cache_miss_tokens": getattr(usage, "prompt_cache_miss_tokens", None),
    }
    cost, tier = estimated_cost(token_usage, response.created)
    return {
        "verdicts": verdicts,
        "usage": token_usage,
        "latency_seconds": round(latency, 3),
        "cost_usd_estimate": cost,
        "pricing_tier": tier,
    }
