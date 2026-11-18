"""One approved definition file feeds keys, keyed prompts, and review output."""

import json
from pathlib import Path

import pymupdf

from run_eval import load_truth
from src.core_pipeline import run_text_page
from src.field_definitions import load_field_definitions


ROOT = Path(__file__).resolve().parents[1]


def test_approved_file_covers_every_human_key_once():
    definitions = load_field_definitions()
    assert len(definitions["shared_rules"]) == 5
    expected = {}
    for path in (ROOT / "data" / "ground_truth").glob("*.json"):
        truth = json.loads(path.read_text(encoding="utf-8"))
        expected[truth["doc_id"]] = {field["field"] for field in truth["fields"]}
    assert {doc: set(fields) for doc, fields in definitions["documents"].items()} == expected
    assert sum(len(fields) for fields in definitions["documents"].values()) == 103


def test_invoice_002_due_date_definition_states_field_boundary_only():
    definition = load_field_definitions()["documents"]["invoice_002"]["due_date"]
    assert definition == "The payment-due date; excludes the invoice issue date."


def test_loaded_answer_key_receives_definitions_from_approved_file():
    path = ROOT / "data" / "ground_truth" / "invoice_001.json"
    with pymupdf.open(ROOT / "data" / "pdfs" / "invoice_001.pdf") as pdf:
        truth = load_truth(path, "invoice_001", len(pdf))
    definitions = load_field_definitions()
    assert truth["shared_rules"] == definitions["shared_rules"]
    assert {field["field"]: field["definition"] for field in truth["fields"]} == (
        definitions["documents"]["invoice_001"])


def test_keyed_prompt_and_review_use_the_same_definitions(tmp_path):
    path = ROOT / "data" / "ground_truth" / "invoice_001.json"
    with pymupdf.open(ROOT / "data" / "pdfs" / "invoice_001.pdf") as pdf:
        truth = load_truth(path, "invoice_001", len(pdf))
    key = {item["field"]: {name: value for name, value in item.items()
                           if name not in {"field", "page"}}
           for item in truth["fields"] if item["page"] == 1}
    definitions = load_field_definitions()
    seen = []

    def recorded(messages):
        seen.append(messages)
        filename = ("day2_invoice_keyed.json" if len(seen) == 1
                    else "day2_invoice_open.json")
        return {"content": (ROOT / "tests" / "fixtures" / filename).read_text(
            encoding="utf-8"), "finish_reason": "stop", "usage": {},
                "api_created_at": None, "latency_seconds": 0.0}

    work = run_text_page("invoice_001", ROOT / "data" / "pdfs" / "invoice_001.pdf",
                         1, truth["source_url"], answer_key=key, output_root=tmp_path,
                         model_request=recorded)
    assert len(seen) == 2
    keyed_text = "\n".join(message["content"] for message in seen[0])
    for rule in definitions["shared_rules"]:
        assert rule in keyed_text
    for field, definition in definitions["documents"]["invoice_001"].items():
        assert field in keyed_text
        assert definition in keyed_text
    review = json.loads((work / "review.json").read_text(encoding="utf-8"))
    assert review["shared_rules"] == definitions["shared_rules"]
    assert review["field_definitions"] == definitions["documents"]["invoice_001"]


def test_definitions_do_not_describe_whether_a_field_is_filled_in():
    definitions = load_field_definitions()["documents"]
    wording = [meaning.casefold() for fields in definitions.values() for meaning in fields.values()]
    for hint in ("entered", "empty", "blank", "if present", "return null"):
        assert not [meaning for meaning in wording if hint in meaning], hint
