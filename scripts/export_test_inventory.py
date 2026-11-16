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
    "test_day2_text_layer_cause": "Historical Day 2 canned W-2 reply with a null tax year and wrong withheld-tax value; replaced by saved real replies.",
    "test_day2_w2_real_replay": "The public W-2 PDF and saved real keyed and open model replies from the live run.",
    "test_daily_comparison": "Two small field maps with one pass-to-fail and one fail-to-pass change.",
    "test_day2_summary": "Saved synthetic run JSON with states, scores, failures, and an incomplete page.",
    "test_development_compare": "Two saved development-run fixtures with same or changed fingerprints.",
    "test_development_run": "All 20 public PDFs, recorded replies, and cached scan text; no network.",
    "test_environments": "Temporary environment variables, blocked socket, result paths, and held-back freeze file.",
    "test_evidence": "Self-made text PDFs with correct, missing, or misplaced quotes and boxes.",
    "test_fact_kinds": "A self-made page and recorded open facts covering every kind plus unclassified.",
    "test_injection_replay": "Recorded baseline and three attack pages on legacy one-call src.extract; the current two-call pipeline is not exercised.",
    "test_injection_two_call": "Four self-made PDF pages and their saved live keyed and open replies on the current two-call path.",
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
    "test_w2_printed_tax_year_is_kept_as_a_finding":
        "The answer-key review keeps the printed W-2 tax-year issue visible as a finding.",
    "test_owner_sheet_has_neutral_shuffled_ids_and_no_answer_hints":
        "The owner review sheet uses shuffled neutral IDs and reveals no answer hints.",
    "test_candidates_are_not_duplicate_rows_for_same_field":
        "The calibration candidates contain no duplicate row for the same field.",
    "test_text_page_writes_full_report_manifest_and_near_match_queue":
        "A text-page run writes a full report, a manifest, and a near-match review queue.",
    "test_line_item_object_is_preserved_and_missing_columns_is_a_failed_fact":
        "A line item keeps its table columns, and an item without columns is a failed fact.",
    "test_score_records_passes_key_currency_metadata_to_exact_comparison":
        "Exact money comparison receives the answer key's printed-currency metadata.",
    "test_keyed_near_match_stays_in_queue_with_same_named_open_fact":
        "A keyed near-match stays in review when an open fact uses the same relation name.",
    "test_run_is_local_cached_and_awaits_owner_review":
        "The calibration run uses the local cached judge and waits for owner review.",
    "test_heldback_refuses_unfrozen_set":
        "The held-back run is refused until its input set is frozen.",
    "test_year_inside_reference_id_does_not_verify_tax_year":
        "A year found only inside an identifier does not verify the tax-year field.",
    "test_review_csv_can_calibrate_without_editing_proposals":
        "Owner labels in the review CSV calibrate the judge without editing proposals.",
    "test_calibration_file_uses_human_labels_not_proposals":
        "The calibration file uses human labels rather than proposed answers.",
    "test_all_twelve_rules_have_named_tests":
        "The suite names a test for each of the twelve hard rules.",
    "test_weekday_and_month_abbreviations_without_added_year":
        "Weekday and month abbreviations normalize without adding an unprinted year.",
    "test_cli_loads_all_confirmed_money_keys":
        "The CLI loads every owner-confirmed money key.",
    "test_requested_mix_and_document_coverage":
        "The calibration sheet includes the requested case mix and document coverage.",
    "test_rule_01_no_score_without_human_key":
        "A fact without a human answer key is reported as extracted and unscored.",
    "test_rule_02_only_three_fact_states":
        "Fact validation rejects states outside verified, uncertain, and failed.",
    "test_rule_03_fabricated_quote_cannot_be_verified":
        "A fabricated quote remains uncertain and receives no verified box.",
    "test_rule_04_single_vision_reading_cannot_verify_a_scan":
        "A scan checked only against its own vision reading remains uncertain.",
    "test_rule_05_simulated_timeout_is_a_recorded_failure":
        "An OCR timeout produces an incomplete run with a named OCR failure.",
    "test_rule_06_mismatched_counts_block_report":
        "A report is rejected when the fact counts do not add up.",
    "test_rule_07_inferred_fact_and_null_are_not_guesses":
        "An inferred fact cannot be verified; an explicit null is a scored abstention, not an uncertain fact.",
    "test_rule_08_judge_requires_other_model_and_wrong_examples":
        "Judge calibration rejects the extractor model and unbalanced examples while keeping exact and judge scores separate.",
    "test_rule_09_document_instruction_stays_data":
        "Page instructions stay in the user message and do not enter the system prompt.",
    "test_rule_10_manifest_records_hashes_and_cache_use":
        "The run manifest records model label, prompt and input hashes, code version, and cache use.",
    "test_rule_11_general_claim_rejected_for_narrow_test":
        "A narrow test cannot be reported as a general document-type claim.",
    "test_rule_12_suite_must_cover_every_hard_rule":
        "The coverage check rejects a list missing any of the twelve named hard-rule tests.",
    "test_w2_missing_labels_are_text_layer_root_causes":
        "The historical canned reply assigns text_layer root causes to two failed fields; it does not replay a real W-2 response.",
    "test_recorded_extraction_ignores_embedded_instructions":
        "The legacy one-call replay preserves its recorded fields; it does not establish current two-call instruction resistance.",
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

HISTORICAL_ASSERTIONS = {
    ("test_day2_text_layer_cause", "test_w2_missing_labels_are_text_layer_root_causes"):
        "causes['tax_year']['stage'] == 'text_layer'; "
        "causes['federal_income_tax_withheld']['stage'] == 'text_layer'",
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
                humanize(base).rstrip(".") + ".")}


def _assertions(module: str, name: str) -> str:
    if (module, name) in HISTORICAL_ASSERTIONS:
        return HISTORICAL_ASSERTIONS[(module, name)]
    path = ROOT / "tests" / f"{module}.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            conditions = []
            for item in ast.walk(node):
                if isinstance(item, ast.Assert):
                    conditions.append(ast.unparse(item.test))
                elif isinstance(item, ast.With) and any(
                    isinstance(context.context_expr, ast.Call)
                    and isinstance(context.context_expr.func, ast.Attribute)
                    and isinstance(context.context_expr.func.value, ast.Name)
                    and context.context_expr.func.value.id == "pytest"
                    and context.context_expr.func.attr == "raises"
                    for context in item.items
                ):
                    conditions.append(" ".join(ast.unparse(item).split()))
            if not conditions:
                raise ValueError(f"No explicit assertion found: {module}.{name}")
            return "; ".join(conditions)
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
