"""Versioned safety/recall benchmark for Seller Top 5 decisions.

Contract cases protect decision rules, but they are not evidence of real-world
accuracy.  Real precision/recall is reported only for completed trades with a
known outcome; observed UI regressions and synthetic adversarial cases remain
separate cohorts.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from src.seller_profit_display import build_seller_net_profit_summary, known_negative_net_profit
from src.seller_top5 import seller_has_positive_purchase_price, seller_result_tier


ALLOWED_SOURCE_KINDS = {
    "observed_ui_regression",
    "synthetic_safety",
    "synthetic_positive_control",
    "completed_real_trade",
}
REAL_VALIDATION_TARGET = 50


def _pct(part: int, whole: int) -> float | None:
    return round(100.0 * part / whole, 1) if whole else None


def _validate_case(case: dict, position: int) -> list[str]:
    errors: list[str] = []
    case_id = str(case.get("id") or "").strip()
    if not case_id:
        errors.append(f"case[{position}] saknar id")
    source_kind = str(case.get("source_kind") or "").strip()
    if source_kind not in ALLOWED_SOURCE_KINDS:
        errors.append(f"{case_id or position}: ogiltig source_kind")
    if not isinstance(case.get("row"), dict):
        errors.append(f"{case_id or position}: row måste vara ett objekt")
    if not isinstance(case.get("expected_find"), bool):
        errors.append(f"{case_id or position}: expected_find måste vara bool")
    if not isinstance(case.get("expected_highlight"), bool):
        errors.append(f"{case_id or position}: expected_highlight måste vara bool")
    if source_kind == "completed_real_trade" and case.get("outcome_verified") is not True:
        errors.append(f"{case_id or position}: verklig affär saknar outcome_verified=true")
    return errors


def evaluate_seller_quality_portfolio(cases: Iterable[dict]) -> dict[str, Any]:
    rows = [dict(case) for case in (cases or []) if isinstance(case, dict)]
    errors: list[str] = []
    seen: set[str] = set()
    for position, case in enumerate(rows):
        errors.extend(_validate_case(case, position))
        case_id = str(case.get("id") or "").strip()
        if case_id and case_id in seen:
            errors.append(f"duplicerat case-id: {case_id}")
        seen.add(case_id)

    results = []
    for case in rows:
        row = dict(case.get("row") or {})
        tier = seller_result_tier(row)
        profit = build_seller_net_profit_summary(row)
        predicted_find = tier == "FIND"
        predicted_highlight = bool(
            tier != "WEAK"
            and seller_has_positive_purchase_price(row)
            and not known_negative_net_profit(row)
            and profit.get("available")
            and float(profit.get("value") or 0) > 0
        )
        expected_find = case.get("expected_find") is True
        expected_highlight = case.get("expected_highlight") is True
        results.append({
            "id": case.get("id"),
            "source_kind": case.get("source_kind"),
            "sport": case.get("sport"),
            "predicted_tier": tier,
            "predicted_find": predicted_find,
            "predicted_highlight": predicted_highlight,
            "expected_find": expected_find,
            "expected_highlight": expected_highlight,
            "find_correct": predicted_find == expected_find,
            "highlight_correct": predicted_highlight == expected_highlight,
            "profit_basis": profit.get("basis"),
        })

    expected_positive = [row for row in results if row["expected_find"]]
    predicted_positive = [row for row in results if row["predicted_find"]]
    true_positive = [row for row in predicted_positive if row["expected_find"]]
    false_positive = [row for row in predicted_positive if not row["expected_find"]]
    false_negative = [row for row in expected_positive if not row["predicted_find"]]
    highlight_misses = [row for row in results if not row["highlight_correct"]]
    safety_rows = [row for row in results if not row["expected_find"]]
    safety_passed = [row for row in safety_rows if not row["predicted_find"]]

    real_rows = [row for row in results if row["source_kind"] == "completed_real_trade"]
    real_expected = [row for row in real_rows if row["expected_find"]]
    real_predicted = [row for row in real_rows if row["predicted_find"]]
    real_true_positive = [row for row in real_predicted if row["expected_find"]]

    cohort_counts = Counter(str(row["source_kind"]) for row in results)
    contract_passed = not errors and not false_positive and not false_negative and not highlight_misses
    return {
        "schema_valid": not errors,
        "schema_errors": errors,
        "case_count": len(results),
        "cohort_counts": dict(sorted(cohort_counts.items())),
        "contract_passed": contract_passed,
        "contract_precision_pct": _pct(len(true_positive), len(predicted_positive)),
        "contract_recall_pct": _pct(len(true_positive), len(expected_positive)),
        "safety_specificity_pct": _pct(len(safety_passed), len(safety_rows)),
        "false_positive_ids": [str(row["id"]) for row in false_positive],
        "false_negative_ids": [str(row["id"]) for row in false_negative],
        "highlight_mismatch_ids": [str(row["id"]) for row in highlight_misses],
        "real_completed_trade_count": len(real_rows),
        "real_validation_target": REAL_VALIDATION_TARGET,
        "real_validation_remaining": max(0, REAL_VALIDATION_TARGET - len(real_rows)),
        "real_precision_pct": _pct(len(real_true_positive), len(real_predicted)),
        "real_recall_pct": _pct(len(real_true_positive), len(real_expected)),
        "real_accuracy_measured": bool(real_rows and real_expected),
        "release_gate": "PASS" if contract_passed else "FAIL",
        "product_validation_status": (
            "REAL_VALIDATION_READY" if len(real_rows) >= REAL_VALIDATION_TARGET
            else "COLLECTING_REAL_OUTCOMES"
        ),
        "results": results,
        "note": (
            "Kontraktsmått från syntetiska fall och observerade UI-regressioner visar endast att säkerhetsreglerna "
            "fungerar som avsett. Verklig precision/recall redovisas separat och kräver verifierade avslut."
        ),
    }
