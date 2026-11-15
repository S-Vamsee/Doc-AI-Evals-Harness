"""Cross-day comparison keeps a failed field visible when the pipeline changes."""

from scripts.compare_daily import compare_field_maps


def test_daily_comparison_reports_worse_and_better_fields_with_cause():
    old = {("invoice", 1, "total"): {"exact": "pass", "extracted": "$10"},
           ("invoice", 1, "date"): {"exact": "fail", "extracted": None}}
    new = {("invoice", 1, "total"): {"exact": "fail", "extracted": "$11",
                                     "root_cause": {"stage": "normalization",
                                                    "reason": "wrong amount"}},
           ("invoice", 1, "date"): {"exact": "pass", "extracted": "2026-11-15"}}
    result = compare_field_maps(old, new)
    assert result["counts"] == {"better": 1, "worse": 1,
                                "unchanged": 0, "changed_no_flip": 0}
    assert result["worse"][0]["root_cause"]["stage"] == "normalization"
