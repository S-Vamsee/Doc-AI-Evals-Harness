"""Deterministic exact-match and text-grounding scores."""

from __future__ import annotations

import calendar
import re
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from src.policy import typed_equal

SMALL_NUMBER_WORDS = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
)


def _plain(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    text = text.translate(str.maketrans({"’": "'", "‘": "'", "–": "-", "—": "-", "�": "-"}))
    return " ".join(text.split())


def _date(value: object) -> str:
    text = _plain(value).replace(".", "")
    text = re.sub(
        r"^(?:mon(?:day)?|tue(?:sday)?|wed(?:nesday)?|thu(?:rsday)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?),?\s+",
        "", text,
    )
    text = re.sub(r"\b(\d{1,2})(?:st|nd|rd|th)\b", r"\1", text)
    text = text.replace(" day of ", " ")
    for fmt in (
        "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y",
        "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y",
    ):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return text


def _month_period(value: object) -> tuple[str, str] | str:
    text = _plain(value)
    iso = re.fullmatch(r"(\d{4}-\d{2})\s*(?:to|-)\s*(\d{4}-\d{2})", text)
    if iso:
        return iso.group(1), iso.group(2)
    named = re.fullmatch(r"([a-z]+)\s+(\d{4})\s*(?:to|-)\s*([a-z]+)\s+(\d{4})", text)
    if named:
        months = {name.casefold(): number for number, name in enumerate(calendar.month_name) if name}
        months.update({name.casefold(): number for number, name in enumerate(calendar.month_abbr) if name})
        first, second = months.get(named.group(1)), months.get(named.group(3))
        if first and second:
            return f"{named.group(2)}-{first:02d}", f"{named.group(4)}-{second:02d}"
    return text


def _amount(value: object) -> Decimal | str:
    text = _plain(value).replace(",", "").replace("$", "").replace("£", "").replace("₹", "")
    text = text.strip()
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        return Decimal(text)
    except InvalidOperation:
        return text


def normalize(field: str, value: object, expected: object) -> object:
    if value is None:
        return None
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return _amount(value)
    if field.endswith("_period"):
        return _month_period(value)
    if "date" in field or "period_end" in field or "period_start" in field:
        return _date(value)
    return _plain(value)


def appears_in_text(field: str, value: object, pages: list[str]) -> bool:
    if value is None:
        return False
    text = _plain(" ".join(pages))
    if isinstance(value, str) and field.endswith(("_number", "_id", "_code", "_reference")):
        return _plain(value) in text
    if field.endswith("_period"):
        period = _month_period(value)
        if isinstance(period, tuple):
            start, end = period
            first_year, first_month = map(int, start.split("-"))
            last_year, last_month = map(int, end.split("-"))
            variants = []
            for separator in (" to ", " - "):
                variants.extend((
                    f"{start}{separator}{end}",
                    f"{calendar.month_name[first_month]} {first_year}{separator}{calendar.month_name[last_month]} {last_year}",
                    f"{calendar.month_abbr[first_month]} {first_year}{separator}{calendar.month_abbr[last_month]} {last_year}",
                ))
            return any(_plain(variant) in text for variant in variants)
        return period in text
    if "date" in field or "period_end" in field or "period_start" in field:
        iso = _date(value)
        try:
            date = datetime.strptime(iso, "%Y-%m-%d")
        except ValueError:
            return _plain(value) in text
        variants = [
            iso, date.strftime("%m/%d/%Y"), date.strftime("%m/%d/%y"),
            date.strftime("%d/%m/%Y"), date.strftime("%d/%m/%y"),
            f"{date.month}/{date.day}/{date.year}",
            f"{date.day}/{date.month}/{date.year}",
            f"{date.strftime('%B')} {date.day}, {date.year}",
            f"{date.strftime('%b')} {date.day}, {date.year}",
            f"{date.day} {date.strftime('%B')} {date.year}",
        ]
        suffix = "th" if 11 <= date.day % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(date.day % 10, "th")
        variants.append(f"{date.day}{suffix} day of {date.strftime('%B')} {date.year}")
        return any(_plain(variant) in text for variant in variants)
    amount = _amount(value)
    if isinstance(amount, Decimal):
        digits = re.escape(format(amount, "f").rstrip("0").rstrip(".") if amount % 1 else str(int(amount)))
        whole = f"{int(amount):,}" if amount >= 0 else f"{int(amount):,}"
        candidates = [digits, re.escape(whole), re.escape(f"{amount:,.2f}"), re.escape(f"{amount:.2f}")]
        if any(re.search(rf"(?<![\d.,]){candidate}(?!\d|[.,]\d)", text) for candidate in candidates):
            return True
        if amount == int(amount) and 0 <= amount < len(SMALL_NUMBER_WORDS):
            return bool(re.search(rf"\b{SMALL_NUMBER_WORDS[int(amount)]}\b", text))
        return False
    if field.endswith(("_list", "_types")) and isinstance(value, str) and "," in value:
        return all(_plain(part) in text for part in value.split(",") if part.strip())
    return _plain(value) in text


def estimated_cost(usage: dict, api_created_at: int) -> tuple[float, str]:
    """USD estimate from published Flash token rates, including cache tier."""
    hour = datetime.fromtimestamp(api_created_at, timezone.utc).hour
    weekday = datetime.fromtimestamp(api_created_at, timezone.utc).weekday()
    peak = weekday < 5 and (1 <= hour < 4 or 6 <= hour < 10)
    hit_rate, miss_rate, output_rate = (
        (0.006, 0.30, 1.20) if peak else (0.003, 0.15, 0.60)
    )
    prompt = usage["prompt_tokens"] or 0
    hit = usage.get("prompt_cache_hit_tokens") or 0
    miss = usage.get("prompt_cache_miss_tokens")
    if miss is None:
        miss = max(prompt - hit, 0)
    output = usage["completion_tokens"] or 0
    return round((hit * hit_rate + miss * miss_rate + output * output_rate) / 1_000_000, 8), (
        "peak" if peak else "off_peak"
    )


def score_document(extracted: dict, truth: dict, pages: list[str]) -> dict:
    extracted_by_name = {item["field"]: item for item in extracted["fields"]}
    correct = 0
    grounded = 0
    present = 0
    failures = []
    ungrounded = []
    field_scores = []
    for item in truth["fields"]:
        field = item["field"]
        got = extracted_by_name[field]
        value = got["value"]
        if item.get("type") == "money":
            exact_match = typed_equal(value, item["value"], "money",
                                      printed_marker=item.get("printed_marker"),
                                      marker_scope=item.get("marker_scope", "adjacent"))
        else:
            exact_match = normalize(field, value, item["value"]) == normalize(field, item["value"], item["value"])
        if exact_match:
            correct += 1
        else:
            failures.append({"field": field, "expected": item["value"], "got": value})
        is_grounded = appears_in_text(field, value, pages) if value is not None else None
        if value is not None:
            present += 1
            if is_grounded:
                grounded += 1
            else:
                ungrounded.append({"field": field, "got": value, "source_page": got["source_page"]})
        field_scores.append({
            "field": field, "expected": item["value"], "got": value,
            "exact_match": exact_match, "grounded": is_grounded,
            "judge_match": None,
        })
    total = len(truth["fields"])
    cost, tier = estimated_cost(extracted["usage"], extracted["api_created_at"])
    return {
        "doc_id": truth["doc_id"], "status": "ok", "model": extracted["model"],
        "fields": total, "correct": correct, "accuracy": round(correct / total * 100, 2),
        "extracted_facts": present, "grounded": grounded,
        "groundedness": round(grounded / present * 100, 2) if present else None,
        "cost_usd_estimate": cost, "pricing_tier": tier,
        "latency_seconds": extracted["latency_seconds"], "usage": extracted["usage"],
        "failures": failures, "ungrounded": ungrounded, "field_scores": field_scores,
    }
