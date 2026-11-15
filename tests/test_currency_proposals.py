"""Owner-confirmed currency proposals remain separate from raw key values."""

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_each_money_key_has_one_owner_confirmed_printed_marker():
    expected = {}
    for path in (ROOT / "data" / "ground_truth").glob("*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for field in doc["fields"]:
            if field.get("type") == "money":
                expected[(doc["doc_id"], field["field"])] = (doc["source_url"], field["page"])
    with (ROOT / "data" / "calibration" / "currency_proposals.csv").open(
            newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    actual = {(row["doc_id"], row["field"]): row for row in rows}
    assert len(rows) == len(expected) == len(actual)
    for key, (source_url, page) in expected.items():
        assert actual[key]["source_url"] == source_url
        assert int(actual[key]["page"]) == page
        assert actual[key]["printed_marker_confirmed"] == "true"
        assert actual[key]["key_update_authorized"] == "true"
        assert actual[key]["proposed_currency"] in {
            "INR", "USD", "CAD", "dollar_symbol_unspecified", "not_printed"}


def test_confirmed_currency_metadata_matches_every_proposal():
    with (ROOT / "data/calibration/currency_proposals.csv").open(
            newline="", encoding="utf-8-sig") as stream:
        proposals = {(row["doc_id"], row["field"]): row for row in csv.DictReader(stream)}
    for path in (ROOT / "data/ground_truth").glob("*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for field in doc["fields"]:
            if field.get("type") != "money":
                continue
            proposal = proposals[(doc["doc_id"], field["field"])]
            code = proposal["proposed_currency"]
            expected_code = code if code in {"INR", "USD", "CAD"} else None
            marker = proposal["printed_marker"]
            assert field.get("proposed_currency") == expected_code
            assert field.get("printed_marker") == marker
            assert field.get("currency_basis") == proposal["currency_basis"]
            assert field.get("marker_scope") == proposal["marker_scope"]
            assert field.get("unit_scale") == int(proposal["unit_scale"])


def test_six_currency_codes_are_inferred_but_printed_markers_are_kept():
    inferred = {("invoice_002", "total_amount"),
                ("filing_001", "gross_profit_2024_thousands"),
                ("filing_001", "net_income_2024_thousands"),
                ("w2_001", "social_security_wages"),
                ("w2_001", "wages"),
                ("w2_001", "federal_income_tax_withheld")}
    with (ROOT / "data/calibration/currency_proposals.csv").open(
            newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    assert {(row["doc_id"], row["field"]) for row in rows
            if row["currency_basis"] == "inferred"} == inferred
    filing = [row for row in rows if row["doc_id"] == "filing_001"]
    assert all(row["printed_marker"] == "$" and row["marker_scope"] == "column"
               and row["unit_scale"] == "1000" for row in filing)
