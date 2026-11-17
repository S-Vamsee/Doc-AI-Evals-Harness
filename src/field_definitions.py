"""Read approved shared rules and field meanings from one Markdown source."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re


DEFINITIONS_PATH = Path(__file__).resolve().parents[1] / "data" / "field_definitions.md"
_DOCUMENT = re.compile(r"^## `([^`]+)`$")
_FIELD = re.compile(r"^- `([^`]+)` — (.+)$")
_RULE = re.compile(r"^[1-5]\. (.+)$")


@lru_cache(maxsize=1)
def load_field_definitions() -> dict:
    """Fail if the approved file is absent, incomplete, or ambiguous."""
    shared_rules: list[str] = []
    documents: dict[str, dict[str, str]] = {}
    current: str | None = None
    in_shared = False
    for line in DEFINITIONS_PATH.read_text(encoding="utf-8").splitlines():
        if line == "## Shared rules for every field":
            in_shared = True
            current = None
            continue
        heading = _DOCUMENT.fullmatch(line)
        if heading:
            current = heading.group(1)
            if current in documents:
                raise ValueError(f"Repeated definition document: {current}")
            documents[current] = {}
            in_shared = False
            continue
        if in_shared:
            match = _RULE.fullmatch(line)
            if match:
                shared_rules.append(match.group(1))
        elif current is not None:
            match = _FIELD.fullmatch(line)
            if match:
                name, meaning = match.groups()
                if name in documents[current]:
                    raise ValueError(f"Repeated field definition: {current}.{name}")
                documents[current][name] = meaning
    if len(shared_rules) != 5 or not documents or any(not fields for fields in documents.values()):
        raise ValueError("Approved definitions need five shared rules and document fields")
    return {"shared_rules": shared_rules, "documents": documents}
