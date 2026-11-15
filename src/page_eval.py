"""Private one-page, machine-first relation extraction experiment."""

from __future__ import annotations

import base64
import hashlib
import itertools
import json
import os
import re
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

import pymupdf
from openai import OpenAI

from src.policy import build_extraction_messages

from src.vision import (
    OCR_PROMPT,
    _json_request,
    vision_cache_signature,
    vision_config,
    vision_readiness,
)

ROOT = Path(__file__).resolve().parents[1]
RESULT_ROOT = Path(os.getenv("HARNESS_RESULTS_DIR", str(ROOT / "results")))
PAGE_RESULTS = RESULT_ROOT / "experiments" / "pages"


def _save(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _tokens(value: str) -> list[str]:
    return re.findall(r"[\w]+", value.casefold(), flags=re.UNICODE)


def _bbox_for_quote(words: list[tuple], quote: str) -> list[float] | None:
    stream: list[tuple[str, tuple]] = []
    for word in words:
        stream.extend((token, word) for token in _tokens(str(word[4])))

    def matches(fragment: str) -> list[list[float]]:
        wanted = _tokens(fragment)
        found = []
        for offset in range(len(stream) - len(wanted) + 1):
            selected = stream[offset:offset + len(wanted)]
            if wanted and [item[0] for item in selected] == wanted:
                boxes = [item[1] for item in selected]
                found.append([min(box[0] for box in boxes), min(box[1] for box in boxes),
                              max(box[2] for box in boxes), max(box[3] for box in boxes)])
        return found

    direct = matches(quote)
    if direct:
        return [round(number, 2) for number in direct[0]]
    lines = [line for line in quote.splitlines() if _tokens(line)]
    if not 2 <= len(lines) <= 4:
        return None
    options = [matches(line)[:12] for line in lines]
    if any(not option for option in options):
        return None
    choices = itertools.product(*options)
    best = None
    for boxes in choices:
        merged = [min(box[0] for box in boxes), min(box[1] for box in boxes),
                  max(box[2] for box in boxes), max(box[3] for box in boxes)]
        if merged[3] - merged[1] > 45 or merged[2] - merged[0] > 380:
            continue
        area = (merged[2] - merged[0]) * (merged[3] - merged[1])
        if best is None or area < best[0]:
            best = area, merged
    return [round(number, 2) for number in best[1]] if best else None


def _source_page(pdf_path: Path, page_number: int, work: Path) -> dict:
    with pymupdf.open(pdf_path) as pdf:
        if not 1 <= page_number <= len(pdf):
            raise ValueError(f"Page {page_number} is outside the PDF's {len(pdf)} pages")
        page = pdf[page_number - 1]
        page_text = page.get_text(sort=True).strip()
        if len(page_text) >= 100:
            return {"text": page_text, "words": page.get_text("words"), "mode": "text",
                    "page_size": [page.rect.width, page.rect.height]}
        blocker = vision_readiness()
        if blocker:
            raise RuntimeError(blocker)
        signature = vision_cache_signature(pdf_path)
        cache_path = work / "ocr.json"
        existing = RESULT_ROOT / "ocr" / f"{pdf_path.stem}.json"
        cached = None
        for path in (cache_path, existing):
            if path.exists():
                record = json.loads(path.read_text(encoding="utf-8"))
                if record.get("cache_signature") == signature:
                    if record.get("page_number") == page_number:
                        cached = record.get("text")
                    elif len(record.get("pages", [])) >= page_number:
                        cached = record["pages"][page_number - 1]
                if cached:
                    break
        if cached is None:
            base_url, model = vision_config()
            image_path = work / "page.png"
            page.get_pixmap(matrix=pymupdf.Matrix(150 / 72, 150 / 72), alpha=False).save(image_path)
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": OCR_PROMPT,
                              "images": [base64.b64encode(image_path.read_bytes()).decode("ascii")]}],
                "options": {"temperature": 0, "num_predict": 4096}, "stream": False, "think": False,
            }
            response = _json_request(f"{base_url}/api/chat", payload, timeout=900)
            cached = response.get("message", {}).get("content", "").strip()
            if not cached:
                raise ValueError("Qwen produced no transcription for the selected page")
            _save(cache_path, {"cache_signature": signature, "page_number": page_number,
                               "text": cached, "model": model, "usage": response.get("eval_count")})
        words: list[tuple] = []
        tessdata = os.getenv("TESSDATA_PREFIX")
        if not tessdata and Path(r"C:\Program Files\Tesseract-OCR\tessdata").exists():
            tessdata = r"C:\Program Files\Tesseract-OCR\tessdata"
        try:
            textpage = page.get_textpage_ocr(language="eng", dpi=150, full=True, tessdata=tessdata)
            words = page.get_text("words", textpage=textpage)
        except RuntimeError:
            pass
        return {"text": cached, "words": words, "mode": "vision",
                "page_size": [page.rect.width, page.rect.height]}


def _client() -> tuple[OpenAI, str, str]:
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is missing")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    return OpenAI(api_key=key, base_url=base_url, timeout=180), model, base_url


def _ask(client: OpenAI, model: str, base_url: str, work: Path, label: str,
         system: str, user: str, max_tokens: int = 5000) -> dict:
    messages = build_extraction_messages(user, system)
    request = {"model": model, "messages": messages,
               "temperature": 0, "response_format": {"type": "json_object"},
               "max_tokens": max_tokens}
    if base_url.rstrip("/") == "https://api.deepseek.com":
        request["extra_body"] = {"thinking": {"type": "disabled"}}
    started = time.perf_counter()
    response = client.chat.completions.create(**request)
    raw = response.choices[0].message.content or ""
    (work / f"{label}.raw.json").write_text(raw + "\n", encoding="utf-8")
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} returned invalid JSON; raw response was saved") from exc
    _save(work / f"{label}.meta.json", {
        "latency_seconds": round(time.perf_counter() - started, 3),
        "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
        "completion_tokens": response.usage.completion_tokens if response.usage else None,
        "prompt_sha256": hashlib.sha256(json.dumps(messages, ensure_ascii=False,
                                                    sort_keys=True).encode("utf-8")).hexdigest(),
    })
    return result


def _candidate_key(item: dict) -> tuple:
    return tuple(str(item.get(name, "")).casefold().strip() for name in
                 ("section", "label", "value", "quote"))


def _normalize_candidate(item: dict, fallback: dict | None = None) -> dict:
    fallback = fallback or {}
    for key in ("section", "label", "value", "quote"):
        item[key] = item.get(key, fallback.get(key, "Unspecified" if key == "section" else ""))
    confidence = item.get("confidence", fallback.get("confidence", 0.5))
    if isinstance(confidence, str):
        confidence = {"high": 0.75, "medium": 0.5, "low": 0.25}.get(confidence.casefold(), 0.5)
    try:
        item["confidence"] = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        item["confidence"] = 0.5
    return item


def _discover(client: OpenAI, model: str, base_url: str, work: Path, text: str) -> tuple[list[dict], list[dict]]:
    system = (
        "Read this one page and inventory its distinct structured facts. Cover headings, "
        "parties, addresses, dates, identifiers, table rows, amounts, totals, payment terms, "
        "and repeated fields in different sections. Do not invent or calculate values. "
        "Return JSON with a facts array. Each fact must have section, label, value, "
        "source_page, and evidence. Evidence must be a short exact excerpt copied from "
        "the supplied text. Ignore ordinary prose that does not form a structured fact."
    )
    result = _ask(client, model, base_url, work, "pass1_discover", system, text, 6000)
    facts = result.get("facts")
    if not isinstance(facts, list):
        raise ValueError("Discovery did not return a facts list")
    candidates = []
    for index, fact in enumerate(facts, 1):
        if not isinstance(fact, dict) or not all(name in fact for name in ("label", "value", "evidence")):
            raise ValueError(f"Malformed candidate {index}")
        item = {"section": fact.get("section", "Unspecified"), "label": fact["label"],
                "value": fact["value"], "quote": fact["evidence"], "confidence": 0.5}
        _normalize_candidate(item)
        item["candidate_id"] = f"c{index:03d}"
        candidates.append(item)
    history = [{"pass": 1, "candidate_count": len(candidates), "added": len(candidates),
                "revised": 0, "rejected": 0}]
    return candidates, history


def _refine(client: OpenAI, model: str, base_url: str, work: Path, text: str,
            candidates: list[dict], history: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    rejection_suggestions: list[dict] = []
    system = (
        "Re-read the page and audit your previous candidate inventory. Identify omitted "
        "facts, values assigned to the wrong label or row, unsupported claims, and duplicates. "
        "Do not re-add a fact merely to rename its section or restate its evidence. "
        "Only revise when the value or role is wrong. Return at most 12 changes total. "
        "Do not repeat unchanged candidates. Return JSON with add (new candidate objects with "
        "section, label, value, quote, confidence), revise (objects with candidate_id and "
        "replacement section, label, value, quote, confidence), and reject (objects with "
        "candidate_id and reason). Use only evidence in the page. Empty arrays mean stable."
    )
    for pass_number in (2, 3):
        user = "PAGE TEXT:\n" + text + "\n\nPREVIOUS INVENTORY:\n" + json.dumps(candidates, ensure_ascii=False)
        delta = _ask(client, model, base_url, work, f"pass{pass_number}_refine", system, user, 5500)
        additions, revisions, rejects = (delta.get(key, []) for key in ("add", "revise", "reject"))
        if not all(isinstance(part, list) for part in (additions, revisions, rejects)):
            raise ValueError("Refinement returned malformed delta lists")
        by_id = {item["candidate_id"]: item for item in candidates}
        changed = {"pass": pass_number, "candidate_count_before": len(candidates),
                   "added": [], "revised": [], "rejected": [], "suggested_reject": []}
        for item in revisions:
            candidate_id = item.get("candidate_id")
            if candidate_id not in by_id:
                raise ValueError(f"Unknown candidate in refinement: {candidate_id}")
            replacement = _normalize_candidate(dict(item), by_id[candidate_id])
            replacement["candidate_id"] = candidate_id
            if _candidate_key(replacement) != _candidate_key(by_id[candidate_id]):
                by_id[candidate_id] = replacement
                changed["revised"].append(candidate_id)
        for item in rejects:
            candidate_id = item.get("candidate_id")
            if candidate_id in by_id:
                reason = str(item.get("reason", ""))
                if "no change needed" not in reason.casefold():
                    rejection_suggestions.append({"candidate_id": candidate_id, "reason": reason,
                                                  "candidate": by_id[candidate_id]})
                    changed["suggested_reject"].append(candidate_id)
        seen = {_candidate_key(item) for item in by_id.values()}
        next_id = max((int(key[1:]) for key in by_id if re.fullmatch(r"c\d+", key)), default=0) + 1
        for item in additions:
            if not all(key in item for key in ("label", "value", "quote")):
                raise ValueError("Malformed added candidate")
            _normalize_candidate(item)
            key = _candidate_key(item)
            if key not in seen:
                item["candidate_id"] = f"c{next_id:03d}"
                next_id += 1
                by_id[item["candidate_id"]] = item
                seen.add(key)
                changed["added"].append(item["candidate_id"])
        candidates = list(by_id.values())
        changed["candidate_count_after"] = len(candidates)
        history.append(changed)
        _save(work / f"pass{pass_number}_inventory.json", candidates)
        print(f"  pass {pass_number}: +{len(changed['added'])}, revised {len(changed['revised'])}, rejection suggestions {len(changed['suggested_reject'])}", flush=True)
        if not any(changed[key] for key in ("added", "revised", "rejected")):
            break
    return candidates, history, rejection_suggestions


def _entities(client: OpenAI, model: str, base_url: str, work: Path, text: str,
              page_number: int, words: list[tuple]) -> list[dict]:
    system = (
        "Identify the distinct entities explicitly present on this document page. Include "
        "the page's main record, people, organizations, accounts, orders, and other objects "
        "that can be subjects or objects of relations. Do not invent entities. Return JSON "
        "with entities array; each entry has entity_id (e001, e002...), type, name, quote. "
        "Quote must be an exact short substring of the supplied page text naming the entity."
    )
    result = _ask(client, model, base_url, work, "entities", system, text, 2200)
    entities = result.get("entities")
    if not isinstance(entities, list):
        raise ValueError("Entity discovery returned no entities array")
    ids = set()
    for item in entities:
        if not isinstance(item, dict) or not all(key in item for key in ("entity_id", "type", "name", "quote")):
            raise ValueError("Malformed entity")
        if item["entity_id"] in ids:
            raise ValueError("Duplicate entity ID")
        ids.add(item["entity_id"])
        quote = str(item["quote"])
        item["source"] = {"page": page_number, "quote": quote,
                          "bbox": _bbox_for_quote(words, quote)}
    return entities


def _relations(client: OpenAI, model: str, base_url: str, work: Path, text: str,
               page_number: int, words: list[tuple], candidates: list[dict],
               entities: list[dict]) -> list[dict]:
    system = (
        "Convert EVERY candidate into one semantic relation. Preserve its candidate_id "
        "as relation_id by changing c to r (c001 becomes r001). Choose a relation type "
        "from the document's meaning, not a fixed taxonomy. Subject is the specific entity "
        "that the fact is about; use an entity_id from the supplied list when possible, "
        "otherwise an explicit descriptive name. Object is a linked entity_id or the "
        "literal value. Value is the literal value if present, otherwise null. Keep distinct "
        "table rows linked to their own order or item. Return JSON with relations array; "
        "each entry has relation_id, type, subject, object, value, confidence. "
        "Return relations in the exact order of the candidates. Do not restart numbering "
        "for each batch or omit candidate IDs."
    )
    relations = []
    for start in range(0, len(candidates), 10):
        chunk = candidates[start:start + 10]
        label = f"relations_{start // 10 + 1:02d}"
        user = ("PAGE TEXT:\n" + text + "\n\nENTITIES:\n" + json.dumps(entities, ensure_ascii=False)
                + "\n\nCANDIDATES:\n" + json.dumps(chunk, ensure_ascii=False))
        result = _ask(client, model, base_url, work, label, system, user, 2500)
        mapped = result.get("relations")
        expected = {"r" + item["candidate_id"][1:] for item in chunk}
        if not isinstance(mapped, list) or len(mapped) != len(chunk):
            raise ValueError(f"{label} did not map every candidate exactly once")
        repaired_ids = {item.get("relation_id") for item in mapped} != expected
        if repaired_ids:
            _save(work / f"{label}.id_repair.json", {
                "reason": "Model restarted or altered relation IDs; restored IDs by candidate order.",
                "returned_ids": [item.get("relation_id") for item in mapped],
                "expected_ids": ["r" + item["candidate_id"][1:] for item in chunk],
            })
            for item, candidate in zip(mapped, chunk, strict=True):
                item["relation_id"] = "r" + candidate["candidate_id"][1:]
                item["id_repaired"] = True
        for item in mapped:
            if not all(key in item for key in ("type", "subject", "object", "value", "confidence")):
                raise ValueError(f"{label} returned malformed relation")
            source_candidate = next(c for c in chunk if "r" + c["candidate_id"][1:] == item["relation_id"])
            quote = str(source_candidate["quote"])
            item["source"] = {"page": page_number, "quote": quote,
                              "bbox": _bbox_for_quote(words, quote)}
            item["status"] = "found"
            item["human_verdict"] = None
            try:
                item["confidence"] = max(0.0, min(1.0, float(item["confidence"])))
            except (TypeError, ValueError):
                item["confidence"] = 0.0
        relations.extend(mapped)
    return relations


def _verify_machine(client: OpenAI, model: str, base_url: str, work: Path,
                    text: str, entities: list[dict], relations: list[dict]) -> tuple[list[dict], list[dict]]:
    system = (
        "You are a separate evidence checker. For each proposed relation, check the "
        "specific subject, relation type, and object/value against the supplied page. "
        "A value appearing somewhere on the page is insufficient: it must belong to "
        "that subject and role or table row. Return JSON with verdicts array; each item "
        "has relation_id, verdict (supported, contradicted, or unclear), and reason. "
        "Use unclear when layout or OCR prevents deciding. Do not silently skip any ID."
    )
    verdicts = []
    normalized_text = " ".join(text.casefold().split())
    for start in range(0, len(relations), 10):
        chunk = relations[start:start + 10]
        label = f"verify_{start // 10 + 1:02d}"
        user = ("PAGE TEXT:\n" + text + "\n\nENTITY ID MAP:\n" + json.dumps(entities, ensure_ascii=False)
                + "\n\nRELATIONS:\n" + json.dumps(chunk, ensure_ascii=False))
        result = _ask(client, model, base_url, work, label, system, user, 1800)
        checked = result.get("verdicts")
        expected = {item["relation_id"] for item in chunk}
        if not isinstance(checked, list) or {item.get("relation_id") for item in checked} != expected:
            raise ValueError(f"{label} did not verify every relation exactly once")
        verdicts.extend(checked)
    by_id = {item["relation_id"]: item for item in verdicts}
    for item in relations:
        quote = item["source"]["quote"]
        exact_quote = bool(quote) and " ".join(quote.casefold().split()) in normalized_text
        located = item["source"]["bbox"] is not None
        verdict = by_id[item["relation_id"]]
        if verdict["verdict"] == "contradicted":
            item["status"] = "rejected"
        elif verdict["verdict"] == "supported" and exact_quote and located and not item.get("id_repaired"):
            item["status"] = "verified"
        else:
            item["status"] = "uncertain"
        item["machine_check"] = {"verdict": verdict["verdict"], "reason": verdict["reason"],
                                 "exact_quote": exact_quote, "bbox_located": located}
    return relations, verdicts


def _coherence(client: OpenAI, model: str, base_url: str, work: Path,
               text: str, relations: list[dict]) -> dict:
    system = (
        "Audit the extracted relations as a connected account of this page. Find "
        "contradictions, impossible links, duplicate facts with different values, and "
        "explicit numerical totals that can be checked against their components. "
        "Do not claim completeness. Return JSON with contradictions array (relation_ids, "
        "reason) and calculations array (relation_ids, expression, observed_result, "
        "expected_result, agrees). Only include calculations whose operands are present "
        "in the page text."
    )
    user = "PAGE TEXT:\n" + text + "\n\nRELATIONS:\n" + json.dumps(relations, ensure_ascii=False)
    result = _ask(client, model, base_url, work, "coherence", system, user, 1600)
    if not isinstance(result.get("contradictions"), list) or not isinstance(result.get("calculations"), list):
        raise ValueError("Coherence checker returned malformed arrays")
    for check in result["calculations"]:
        expression = str(check.get("expression", "")).replace(",", "").replace("$", "")
        expression = expression.split("=", 1)[0].strip()
        addition = re.fullmatch(r"(\d+(?:\.\d+)?)\s*\+\s*(\d+(?:\.\d+)?)", expression)
        percent = re.fullmatch(r"(\d+(?:\.\d+)?)%\s+of\s+(\d+(?:\.\d+)?)", expression, re.I)
        try:
            expected = Decimal(str(check.get("expected_result", "")).replace(",", "").replace("$", ""))
            if addition:
                calculated = Decimal(addition.group(1)) + Decimal(addition.group(2))
            elif percent:
                calculated = (Decimal(percent.group(1)) * Decimal(percent.group(2)) / 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                calculated = None
            check["python_result"] = str(calculated) if calculated is not None else None
            check["python_agrees"] = calculated == expected if calculated is not None else None
        except (InvalidOperation, TypeError):
            check["python_result"] = None
            check["python_agrees"] = None
    return result


def run_page(page_id: str, pdf_path: Path, page_number: int, source_url: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", page_id)
    work = PAGE_RESULTS / safe / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    work.mkdir(parents=True, exist_ok=True)
    source = _source_page(pdf_path, page_number, work)
    _save(work / "source.json", {"page_id": page_id, "pdf_path": str(pdf_path.resolve()),
                                 "pdf_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
                                 "source_url": source_url, "page_number": page_number,
                                 "mode": source["mode"], "page_size": source["page_size"],
                                 "page_text_sha256": hashlib.sha256(source["text"].encode()).hexdigest()})
    (work / "page_text.txt").write_text(source["text"], encoding="utf-8")
    client, model, base_url = _client()
    print("Discovering page facts...", flush=True)
    candidates, history = _discover(client, model, base_url, work, source["text"])
    _save(work / "pass1_inventory.json", candidates)
    print(f"  pass 1: {len(candidates)} candidates", flush=True)
    candidates, history, rejection_suggestions = _refine(client, model, base_url, work, source["text"], candidates, history)
    print("Linking entities and relations...", flush=True)
    entities = _entities(client, model, base_url, work, source["text"], page_number, source["words"])
    relations = _relations(client, model, base_url, work, source["text"], page_number,
                           source["words"], candidates, entities)
    print("Checking each relation and page coherence...", flush=True)
    relations, verdicts = _verify_machine(client, model, base_url, work, source["text"], entities, relations)
    coherence = _coherence(client, model, base_url, work, source["text"], relations)
    by_relation_id = {item["relation_id"]: item for item in relations}
    for conflict in coherence["contradictions"]:
        for relation_id in conflict.get("relation_ids", []):
            if relation_id in by_relation_id and by_relation_id[relation_id]["status"] == "verified":
                by_relation_id[relation_id]["status"] = "uncertain"
                by_relation_id[relation_id]["machine_check"]["coherence_conflict"] = conflict.get("reason")
    result = {"page_id": page_id, "run_at_utc": datetime.now(timezone.utc).isoformat(),
              "pdf_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
              "source_url": source_url, "page_number": page_number, "mode": source["mode"],
              "model": "deepseek-flash", "candidate_count": len(candidates),
              "entities": entities, "relations": relations, "rejection_suggestions": rejection_suggestions,
              "passes": history, "machine_verdicts": verdicts, "coherence": coherence,
              "stable": not any(history[-1].get(key) for key in ("added", "revised", "rejected")),
              "human_verification": "pending"}
    _save(work / "machine.json", result)
    counts = {status: sum(item["status"] == status for item in relations)
              for status in ("found", "verified", "uncertain", "rejected")}
    lines = [f"# One-page machine extraction: {page_id}", "",
             f"Source: {source_url}", "", f"Candidates: {len(candidates)}; entities: {len(entities)}; relations: {len(relations)}.",
             f"Machine status: {counts}.", f"Passes: {len(history)}. Human verification: pending.",
             f"Candidate inventory stable: {result['stable']}.",
             "", "Machine-verified means the separate checker supported the relation, the exact quote "
             "is in the page transcription, and a bounding box was located. It is not a human verdict.",
             "", f"Unresolved coherence contradictions: {len(coherence['contradictions'])}.", ""]
    (work / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("Saved private machine run:", work, flush=True)
    return work


def compare_page(machine_path: Path, verification_path: Path) -> Path:
    machine = json.loads(machine_path.read_text(encoding="utf-8"))
    human = json.loads(verification_path.read_text(encoding="utf-8"))
    if human.get("page_id") != machine["page_id"] or human.get("pdf_sha256") != machine["pdf_sha256"]:
        raise ValueError("Human verification is for a different page or PDF")
    verdicts = human.get("verdicts")
    missing = human.get("missing_relations")
    if not isinstance(verdicts, list) or not isinstance(missing, list):
        raise ValueError("Verification needs verdicts and missing_relations arrays")
    by_id = {item["relation_id"]: item for item in verdicts}
    relations = machine["relations"]
    if set(by_id) != {item["relation_id"] for item in relations} or len(by_id) != len(verdicts):
        raise ValueError("Human verification must cover every machine relation exactly once")
    if any(item.get("human_verdict") not in {"right", "wrong", "missing"} for item in verdicts):
        raise ValueError("Invalid human verdict")
    right = sum(item["human_verdict"] == "right" for item in verdicts)
    wrong = sum(item["human_verdict"] == "wrong" for item in verdicts)
    missed = len(missing) + sum(item["human_verdict"] == "missing" for item in verdicts)
    coverage_denominator = right + missed
    correctness_denominator = right + wrong
    result = {"page_id": machine["page_id"], "human_verified_at_utc": datetime.now(timezone.utc).isoformat(),
              "machine_run": str(machine_path), "right": right, "wrong": wrong, "missed": missed,
              "coverage": round(right / coverage_denominator * 100, 2) if coverage_denominator else None,
              "correctness": round(right / correctness_denominator * 100, 2) if correctness_denominator else None,
              "machine_verified_human_wrong": [item["relation_id"] for item in verdicts
                                               if item["human_verdict"] == "wrong"
                                               and next(r for r in relations if r["relation_id"] == item["relation_id"])["status"] == "verified"],
              "gap": {"wrong": [item for item in verdicts if item["human_verdict"] == "wrong"],
                      "missing": missing},
              "coherence": machine["coherence"],
              "human_effort": {"corrected_or_added": wrong + missed,
                               "minutes": human.get("minutes_spent")},
              "passes": machine["passes"]}
    output = machine_path.parent / "human_comparison.json"
    _save(output, result)
    return output
