"""Export each offline pytest case with its input and expected outcome."""

from __future__ import annotations

import ast
import csv
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]

MODULE_INPUTS = {
    "test_answer_keys": "The 20 public human answer-key JSON files and their field metadata.",
    "test_calibration_sheet": "The shuffled 60-pair owner review sheet and public source excerpts.",
    "test_code_version": "Two temporary code trees with a changed development runner or review file.",
    "test_core_pipeline": "A self-made invoice PDF and recorded keyed/open model replies or a simulated timeout.",
    "test_currency_proposals": "Owner-confirmed printed-marker proposals and money fields in public answer keys.",
    "test_currency_scoring": "Money pairs with printed symbols, codes, bare values, and column markers.",
    "test_day2_abstention": "A self-made invoice PDF with an empty due date and recorded explicit-null reply.",
    "test_day2_call_isolation": "Recorded keyed and open replies with overlaps, a length-limited open reply, malformed open facts, and a keyed duplicate.",
    "test_day2_keyed_contract": "Recorded keyed JSON with an omitted field, duplicate field, or invalid shape.",
    "test_day2_invoice_replay": "One public invoice PDF and the two saved live model responses from its keyed and open calls.",
    "test_day2_multi_quote_analysis": "Saved quote examples containing bare values and label-and-value phrases.",
    "test_day2_prompt": "The saved keyed and open extraction instruction strings.",
    "test_day2_review_source": "A keyed near-match and an overlapping open fact on the same self-made page.",
    "test_day2_role_support": "A self-made PDF containing only a bare invoice identifier.",
    "test_day2_text_only_run": "All public PDFs with recorded model replies; only keyed pages with text are selected.",
    "test_day2_typed_support": "Self-made PDF lines with a date, currency amount, and embedded number.",
    "test_day2_w2_real_replay": "The public W-2 PDF and saved real keyed and open model replies from the live run.",
    "test_daily_comparison": "Two small field maps with one pass-to-fail and one fail-to-pass change.",
    "test_day2_summary": "Saved synthetic run JSON with states, scores, failures, and an incomplete page.",
    "test_development_compare": "Two saved development-run fixtures with same or changed fingerprints.",
    "test_development_run": "All 20 public PDFs, recorded replies, and cached scan text; no network.",
    "test_environments": "Temporary environment variables, blocked socket, result paths, and held-back freeze file.",
    "test_evidence": "Self-made text PDFs with correct, missing, or misplaced quotes and boxes.",
    "test_fact_kinds": "A self-made page and recorded open facts covering every kind plus unclassified.",
    "test_injection_replay": "Recorded baseline and three pages with embedded instruction attacks.",
    "test_judge_calibration": "Human-labelled value pairs and recorded local-judge verdicts.",
    "test_judge_calibration_run": "Saved calibration rows, local judge fixtures, and disagreement output.",
    "test_live_response_limit": "A fake API reply that reaches the output limit and leaves partial JSON.",
    "test_local_judge": "Fake local Ollama model list and recorded boolean or invalid judge replies.",
    "test_owner_approved_corrections": "The public specimen form and owner-approved symptom answer key.",
    "test_review": "Verified, uncertain, and exact-failed fact records with a small page text.",
    "test_review_rulings": "REVIEW.md rulings and money/name pairs for the scorer and future judge.",
    "test_rule_suite_coverage": "The list of twelve hard-rule test IDs.",
    "test_rules": "Deliberately broken fact, scan, timeout, tally, injection, and manifest fixtures.",
    "test_scan_core": "A blank PDF, cached scan reading, and recorded extraction response.",
    "test_scan_evidence": "Vision text and independently positioned Tesseract words, including mismatches.",
    "test_scoring": "Typed answer-key and candidate pairs for money, dates, IDs, names, and nulls.",
    "test_test_inventory": "A test identifier for an explicit-null invoice case.",
    "test_truth_loading": "Owner-confirmed ground-truth JSON files and document date order.",
    "test_w2_case": "The public W-2 text layer and its printed-year appearance.",
}

EXPECTED_OVERRIDES = {
    "test_explicit_null_is_scored_as_abstention_and_not_reviewed":
        "The null passes a null key, increments abstentions and skipped, and never enters uncertainty or review.",
    "test_keyed_reply_classifies_each_requested_name":
        "The parser keeps the explicit null and names one duplicate and one omitted field as extraction failures.",
    "test_invalid_keyed_shape_is_an_extraction_failure":
        "Malformed keyed JSON is rejected at extraction.",
    "test_omitted_and_duplicate_fields_are_named_failures_in_saved_run":
        "The saved run exits nonzero and lists both failed fields with stage extraction.",
    "test_bare_value_has_separate_role_not_printed_outcome_and_review_sample":
        "The bare identifier stays uncertain, has role_not_printed support, and is sampled for review.",
    "test_w2_missing_labels_are_text_layer_root_causes":
        "Both failed W-2 fields report text_layer as their earliest root-cause stage.",
    "test_text_only_mode_runs_fifteen_public_pdfs_offline":
        "Exactly 15 text PDFs run, each keyed page gets two recorded calls, and scans are excluded.",
    "test_date_and_amount_are_supported_by_typed_printed_forms":
        "Code verifies normalized date and money values only when the printed quote supports them.",
    "test_number_inside_another_number_does_not_count_as_support":
        "302 is uncertain when the quote prints only 3020.",
    "test_unscored_extraction_failure_keeps_requested_fields_in_denominator":
        "Five requested fields on a failed page remain in the score denominator as failures.",
    "test_saved_live_invoice_reply_reproduces_keyed_score_and_fact_states":
        "The offline replay makes two calls to recorded replies and reproduces 25 fact states and a 5/5 keyed score.",
    "test_daily_comparison_reports_worse_and_better_fields_with_cause":
        "The comparison reports one better and one worse field and preserves the worse field's root cause.",
}


def humanize(name: str) -> str:
    name = name.removeprefix("test_").replace("_", " ")
    return name[:1].upper() + name[1:]


def describe_test(classname: str, name: str) -> dict[str, str]:
    module = classname.rsplit(".", 1)[-1]
    if module not in MODULE_INPUTS:
        raise ValueError(f"No input description for {module}")
    base = name.split("[", 1)[0]
    check = humanize(base)
    if "[" in name:
        check += " (" + name.split("[", 1)[1].rstrip("]").replace("_", " ") + ")"
    return {"plain_language_check": check,
            "input": MODULE_INPUTS[module],
            "expected_result": EXPECTED_OVERRIDES.get(base,
                "The asserted outcome holds: " + humanize(base).lower() + ".")}


def _assertions(module: str, name: str) -> str:
    path = ROOT / "tests" / f"{module}.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return "; ".join(ast.unparse(item.test) for item in ast.walk(node)
                             if isinstance(item, ast.Assert))
    raise ValueError(f"Test source not found: {module}.{name}")


def export_inventory(xml_path: Path, csv_path: Path) -> int:
    suite = ET.parse(xml_path).getroot()
    cases = list(suite.iter("testcase"))
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=("test_id", "result",
            "plain_language_check", "input", "expected_result",
            "asserted_conditions", "duration_seconds"))
        writer.writeheader()
        for case in cases:
            classname, name = case.attrib["classname"], case.attrib["name"]
            base = name.split("[", 1)[0]
            module = classname.rsplit(".", 1)[-1]
            row = describe_test(classname, name)
            row.update({"test_id": f"{classname}::{name}",
                        "result": "fail" if case.find("failure") is not None else
                                  "error" if case.find("error") is not None else
                                  "skipped" if case.find("skipped") is not None else "pass",
                        "asserted_conditions": _assertions(module, base),
                        "duration_seconds": case.attrib.get("time", "")})
            writer.writerow(row)
    return len(cases)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: export_test_inventory.py RESULTS.xml OUTPUT.csv")
    print(f"Exported {export_inventory(Path(sys.argv[1]), Path(sys.argv[2]))} tests")
