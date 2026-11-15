"""Owner-approved open extraction kinds and the unclassified count."""

import json

import pymupdf

from src.core_pipeline import SYSTEM_PROMPT, run_text_page


def test_open_extraction_names_every_kind_and_counts_unclassified(tmp_path):
    examples = [
        ("party", "supplier", "Northvale Paper Supply", None),
        ("identifier", "invoice_number", "INV-4102", None),
        ("date_or_time", "invoice_date", "6 October 2026", None),
        ("amount", "total_amount", "$128.40", None),
        ("line_item", "pencils", "Pencils 2 $4.00", {"item": "Pencils", "quantity": "2", "price": "$4.00"}),
        ("labelled_value", "priority", "High", None),
        ("statement", "delivery_note", "Delivery is included.", None),
        ("unclassified", "other_detail", "See attached schedule.", None),
    ]
    prompt_words = ("party", "identifier", "date_or_time", "amount", "line_item",
                    "labelled_value", "statement", "unclassified", "most specific",
                    "one table row", "columns")
    for word in prompt_words:
        assert word in SYSTEM_PROMPT

    path = tmp_path / "facts.pdf"
    pdf = pymupdf.open()
    page = pdf.new_page()
    for index, (_, _, value, _) in enumerate(examples):
        page.insert_text((72, 72 + index * 20), value)
    pdf.save(path)
    pdf.close()
    facts = [{"kind": kind, "subject": None, "relation": relation,
              "value": value, "origin": "extracted", "quote": value,
              "columns": columns} for kind, relation, value, columns in examples]

    def recorded(_messages):
        return {"content": json.dumps({"facts": facts}), "usage": {},
                "api_created_at": None, "latency_seconds": 0.0}

    run = run_text_page("fact_kinds", path, 1, "https://example.org/facts.pdf",
                        output_root=tmp_path / "runs", model_request=recorded)
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    report = (run / "report.md").read_text(encoding="utf-8")
    assert result["complete"] is True
    assert result["kind_counts"] == {kind: 1 for kind, *_ in examples}
    assert result["records"][4]["columns"] == examples[4][3]
    assert "Unclassified facts: 1" in report

