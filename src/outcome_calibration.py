"""Outcome calibration for FlipFynd's real-world flip journal.

This module is deliberately descriptive. It never mutates analyzer weights or
turns a small sample into a model adjustment. Real outcomes are grouped by the
signals captured when the listing was added to Flip Journal.
"""
from __future__ import annotations

from statistics import median
from typing import Any, Iterable, Optional

BASIC_SAMPLE = 5
TENDENCY_SAMPLE = 10
ADJUSTMENT_REVIEW_SAMPLE = 20


def _to_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sold_rows(entries: Iterable[dict]) -> list[dict]:
    rows = []
    for row in entries:
        if row.get("status") != "sålt":
            continue
        if _to_float(row.get("actual_net_profit")) is None:
            continue
        rows.append(row)
    return rows


def sample_level(count: int) -> dict[str, Any]:
    if count < BASIC_SAMPLE:
        return {
            "level": "insufficient",
            "label": "För lite historik",
            "message": f"{count}/{BASIC_SAMPLE} avslut för grundläggande beskrivning.",
            "supports_description": False,
            "supports_tendency": False,
            "supports_adjustment_review": False,
        }
    if count < TENDENCY_SAMPLE:
        return {
            "level": "descriptive",
            "label": "Beskrivande underlag",
            "message": f"{count} avslut. Visa utfall, men dra ingen tydlig modellslutsats ännu.",
            "supports_description": True,
            "supports_tendency": False,
            "supports_adjustment_review": False,
        }
    if count < ADJUSTMENT_REVIEW_SAMPLE:
        return {
            "level": "tendency",
            "label": "Tendens kan bedömas",
            "message": f"{count} avslut. En historisk tendens kan visas, men vikter ändras inte automatiskt.",
            "supports_description": True,
            "supports_tendency": True,
            "supports_adjustment_review": False,
        }
    return {
        "level": "review_ready",
        "label": "Tillräckligt för manuell kalibreringsgranskning",
        "message": f"{count} avslut. Underlaget räcker för att manuellt granska modellvikter; inga vikter ändras automatiskt.",
        "supports_description": True,
        "supports_tendency": True,
        "supports_adjustment_review": True,
    }


def _metrics(rows: list[dict]) -> dict[str, Any]:
    profits = [_to_float(r.get("actual_net_profit")) for r in rows]
    profits = [x for x in profits if x is not None]
    rois = [_to_float(r.get("actual_roi_pct")) for r in rows]
    rois = [x for x in rois if x is not None]
    days = [_to_float(r.get("days_to_sell")) for r in rows]
    days = [x for x in days if x is not None]
    errors = []
    resale_errors = []
    for r in rows:
        expected_profit = _to_float(r.get("expected_net_profit_at_capture"))
        actual_profit = _to_float(r.get("actual_net_profit"))
        if expected_profit is not None and actual_profit is not None:
            errors.append(actual_profit - expected_profit)
        expected_resale = _to_float(r.get("expected_resale_at_capture"))
        actual_sale = _to_float(r.get("sale_price"))
        if expected_resale is not None and actual_sale is not None:
            resale_errors.append(actual_sale - expected_resale)
    count = len(rows)
    gate = sample_level(count)
    return {
        "count": count,
        "sample": gate,
        "win_rate": round(sum(1 for p in profits if p > 0) / len(profits) * 100, 1) if profits else None,
        "median_net_profit": round(median(profits), 2) if profits else None,
        "median_roi_pct": round(median(rois), 1) if rois else None,
        "median_days_to_sell": round(median(days), 1) if days else None,
        "mean_profit_error": round(sum(errors) / len(errors), 2) if errors else None,
        "mean_resale_error": round(sum(resale_errors) / len(resale_errors), 2) if resale_errors else None,
    }


def _signal_memberships(row: dict) -> list[tuple[str, str]]:
    memberships: list[tuple[str, str]] = []
    decision = str(row.get("recommended_decision") or "").strip()
    if decision.startswith("KÖP"):
        memberships.append(("decision_buy", "KÖP-rekommendation"))
    elif decision == "KANSKE":
        memberships.append(("decision_watch", "BEVAKA-rekommendation"))

    if row.get("information_edge_candidate_at_capture"):
        memberships.append(("information_edge", "Informationsövertag"))
    if row.get("hidden_find_candidate_at_capture"):
        memberships.append(("hidden_find", "Dolt fynd"))
    if row.get("market_edge_candidate_at_capture"):
        memberships.append(("market_edge", "Market Edge"))
    if row.get("mispriced_rookie_candidate_at_capture"):
        memberships.append(("rookie_hunter", "Rookie Hunter"))
    if row.get("misclassified_card_candidate_at_capture"):
        memberships.append(("misclassified", "Misclassified Hunter"))

    sport = str(row.get("sport") or "").strip().lower()
    if sport:
        memberships.append((f"sport:{sport}", f"Sport: {sport.capitalize()}"))

    purchase = _to_float(row.get("purchase_price"))
    if purchase is not None:
        if purchase <= 50:
            memberships.append(("price:0-50", "Inköp 0–50 kr"))
        elif purchase <= 100:
            memberships.append(("price:51-100", "Inköp 51–100 kr"))
        elif purchase <= 250:
            memberships.append(("price:101-250", "Inköp 101–250 kr"))
        else:
            memberships.append(("price:250+", "Inköp över 250 kr"))
    return memberships


def build_outcome_calibration(entries: Iterable[dict]) -> dict[str, Any]:
    sold = _sold_rows(entries)
    overall = _metrics(sold)
    grouped: dict[str, dict[str, Any]] = {}
    labels: dict[str, str] = {}
    for row in sold:
        for key, label in _signal_memberships(row):
            labels[key] = label
            grouped.setdefault(key, {"rows": []})["rows"].append(row)

    groups = []
    for key, payload in grouped.items():
        metrics = _metrics(payload["rows"])
        groups.append({"key": key, "label": labels[key], **metrics})
    groups.sort(key=lambda g: (g["count"], g.get("median_net_profit") or -10**9), reverse=True)

    tendency_groups = [g for g in groups if g["sample"]["supports_tendency"]]
    best = None
    worst = None
    if tendency_groups:
        ranked = [g for g in tendency_groups if g.get("median_net_profit") is not None]
        if ranked:
            best = max(ranked, key=lambda g: (g["median_net_profit"], g.get("win_rate") or 0))
            worst = min(ranked, key=lambda g: (g["median_net_profit"], g.get("win_rate") or 0))

    return {
        "sold_count": len(sold),
        "overall": overall,
        "groups": groups,
        "best_tendency": best,
        "worst_tendency": worst,
        "automatic_weight_changes": False,
        "note": (
            "Kalibreringen är beskrivande och bygger bara på verkligt avslutade journalposter. "
            "Den bevisar inte orsakssamband och ändrar aldrig modellvikter automatiskt."
        ),
    }
