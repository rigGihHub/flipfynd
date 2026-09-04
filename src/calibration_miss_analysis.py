"""Explain why real FlipFynd outcomes missed the captured expectation.

The analysis is deliberately descriptive. It classifies only mismatches that can
be supported by fields already stored in Flip Journal. It never changes model
weights automatically and never invents an identity/variant error when no such
correction has been recorded.
"""
from __future__ import annotations

from collections import Counter
from statistics import median
from typing import Any, Iterable, Optional

from src.outcome_review import OUTCOME_REVIEW_REASONS, normalize_review_reasons

MIN_CATEGORY_SAMPLE = 5


def _to_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sold_rows(entries: Iterable[dict]) -> list[dict]:
    return [
        row for row in entries
        if row.get("status") == "sålt" and _to_float(row.get("actual_net_profit")) is not None
    ]


def classify_outcome_misses(row: dict) -> list[dict[str, Any]]:
    """Return evidence-backed miss reasons for one completed journal row."""
    misses: list[dict[str, Any]] = []

    purchase = _to_float(row.get("purchase_price"))
    max_price = _to_float(row.get("max_total_price_at_capture"))
    if purchase is not None and max_price is not None and purchase > max_price:
        misses.append({
            "key": "paid_over_max",
            "label": "Köpte över rekommenderat maxpris",
            "severity": "high",
            "delta": round(purchase - max_price, 2),
            "source": "automatic",
        })

    expected_resale = _to_float(row.get("expected_resale_at_capture"))
    sale_price = _to_float(row.get("sale_price"))
    if expected_resale and sale_price is not None:
        resale_gap = sale_price - expected_resale
        # Ignore tiny noise: require at least 15% and 25 kr downside.
        if resale_gap <= -max(25.0, expected_resale * 0.15):
            misses.append({
                "key": "resale_overestimated",
                "label": "Försäljningsvärdet överskattades",
                "severity": "high",
                "delta": round(resale_gap, 2),
                "source": "automatic",
            })

    expected_profit = _to_float(row.get("expected_net_profit_at_capture"))
    actual_profit = _to_float(row.get("actual_net_profit"))
    if expected_profit is not None and actual_profit is not None:
        profit_gap = actual_profit - expected_profit
        if profit_gap <= -max(25.0, abs(expected_profit) * 0.25):
            misses.append({
                "key": "profit_below_expectation",
                "label": "Nettovinsten blev klart sämre än väntat",
                "severity": "medium",
                "delta": round(profit_gap, 2),
                "source": "automatic",
            })

    predicted_days = _to_float(row.get("flip_velocity_days_at_capture"))
    actual_days = _to_float(row.get("days_to_sell"))
    if predicted_days and actual_days is not None:
        # Require a meaningful miss: >= 7 extra days and >= 50% slower.
        if actual_days >= predicted_days * 1.5 and actual_days - predicted_days >= 7:
            misses.append({
                "key": "slower_than_expected",
                "label": "Kortet tog längre tid att sälja än väntat",
                "severity": "medium",
                "delta": round(actual_days - predicted_days, 1),
                "source": "automatic",
            })

    if actual_profit is not None and actual_profit <= 0:
        misses.append({
            "key": "actual_loss",
            "label": "Affären gav ingen positiv nettovinst",
            "severity": "high",
            "delta": round(actual_profit, 2),
            "source": "automatic",
        })

    # Manual review reasons are explicit user-supplied evidence. They may cover
    # causes that cannot be inferred safely from price/profit fields alone.
    existing_keys = {miss["key"] for miss in misses}
    for reason_key in normalize_review_reasons(row.get("outcome_review_reasons")):
        miss_key = f"manual:{reason_key}"
        if miss_key in existing_keys:
            continue
        misses.append({
            "key": miss_key,
            "label": OUTCOME_REVIEW_REASONS[reason_key],
            "severity": "review",
            "delta": None,
            "source": "manual_review",
        })

    return misses


def build_miss_analysis(entries: Iterable[dict]) -> dict[str, Any]:
    sold = _sold_rows(entries)
    classified = []
    category_rows: dict[str, list[dict]] = {}
    labels: dict[str, str] = {}

    for row in sold:
        misses = classify_outcome_misses(row)
        classified.append({"row": row, "misses": misses})
        for miss in misses:
            key = miss["key"]
            labels[key] = miss["label"]
            category_rows.setdefault(key, []).append({"row": row, "miss": miss})

    groups = []
    for key, records in category_rows.items():
        profits = [_to_float(x["row"].get("actual_net_profit")) for x in records]
        profits = [x for x in profits if x is not None]
        days = [_to_float(x["row"].get("days_to_sell")) for x in records]
        days = [x for x in days if x is not None]
        groups.append({
            "key": key,
            "label": labels[key],
            "count": len(records),
            "share_of_sold_pct": round(len(records) / len(sold) * 100, 1) if sold else 0.0,
            "median_actual_profit": round(median(profits), 2) if profits else None,
            "median_days_to_sell": round(median(days), 1) if days else None,
            "enough_for_pattern": len(records) >= MIN_CATEGORY_SAMPLE,
        })
    groups.sort(key=lambda g: (g["count"], g.get("median_actual_profit") or -10**9), reverse=True)

    miss_counter = Counter()
    for item in classified:
        for miss in item["misses"]:
            miss_counter[miss["key"]] += 1

    rows_with_miss = sum(1 for item in classified if item["misses"])
    primary = groups[0] if groups and groups[0]["enough_for_pattern"] else None

    return {
        "sold_count": len(sold),
        "rows_with_miss": rows_with_miss,
        "rows_without_detected_miss": len(sold) - rows_with_miss,
        "miss_rate_pct": round(rows_with_miss / len(sold) * 100, 1) if sold else None,
        "groups": groups,
        "primary_pattern": primary,
        "automatic_weight_changes": False,
        "identity_miss_assessed": any("manual:identity_wrong" == g["key"] for g in groups),
        "note": (
            "Automatiska missar bygger bara på sparade pris-, vinst- och tidsfält. "
            "Identitet, variant, skick och marknadsorsaker tas bara med när de har markerats manuellt i Outcome Review. "
            "Inga modellvikter ändras automatiskt."
        ),
    }
