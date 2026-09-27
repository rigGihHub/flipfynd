"""Honest Seller Top 5 coverage and labelled-recall diagnostics.

Production inventory has no ground truth, so coverage must not be presented as
recall. Actual recall is measurable only against a labelled benchmark set.
"""
from __future__ import annotations


def _pct(part: int, whole: int) -> float:
    return round(100.0 * max(0, int(part or 0)) / max(1, int(whole or 0)), 1)


def build_seller_coverage_funnel(**counts) -> dict:
    values = {key: max(0, int(value or 0)) for key, value in counts.items()}
    unique = values.get("inventory_unique", 0)
    quick = values.get("quick_success", 0)
    full = values.get("full_success", 0)
    cumulative = values.get("cumulative_full_unique", 0)
    remaining = values.get("cumulative_full_remaining", max(0, unique - cumulative))
    return {
        **values,
        "quick_coverage_pct_this_run": _pct(quick, unique),
        "full_coverage_pct_this_run": _pct(full, unique),
        "cumulative_full_coverage_pct": _pct(cumulative, unique),
        "quick_not_analysed_this_run": max(0, unique - values.get("quick_selected", 0)),
        "full_not_analysed_yet": remaining,
        "inventory_analysis_complete": bool(unique > 0 and remaining == 0),
        "recall_measured": False,
        "recall_note": "Täckning är inte recall. Recall kräver ett separat facit med kända verkliga fynd.",
    }


def evaluate_labelled_recall(expected_opportunity_keys, analysed_keys, surfaced_keys) -> dict:
    """Measure selection and result recall against an explicit ground truth."""
    expected = {str(value) for value in (expected_opportunity_keys or []) if str(value)}
    analysed = {str(value) for value in (analysed_keys or []) if str(value)}
    surfaced = {str(value) for value in (surfaced_keys or []) if str(value)}
    found_in_analysis = expected & analysed
    surfaced_expected = expected & surfaced
    return {
        "expected_opportunities": len(expected),
        "expected_full_analysed": len(found_in_analysis),
        "expected_surfaced": len(surfaced_expected),
        "selection_recall_pct": _pct(len(found_in_analysis), len(expected)) if expected else None,
        "result_recall_pct": _pct(len(surfaced_expected), len(expected)) if expected else None,
        "missed_before_full_analysis": sorted(expected - analysed),
        "missed_after_full_analysis": sorted(found_in_analysis - surfaced),
    }
