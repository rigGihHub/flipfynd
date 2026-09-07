"""Unified manual model-review evidence from completed Flip Journal outcomes.

Combines false-positive and false-negative reviews without inferring causality
or changing model weights. Only completed real-world outcomes are used.
"""
from __future__ import annotations

from statistics import median
from typing import Any, Iterable, Optional

from src.false_positive_review import build_false_positive_review
from src.false_negative_review import build_false_negative_review

MIN_MANUAL_REVIEW_SAMPLE = 20
MIN_SEGMENT_SAMPLE = 5


def _to_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _decision(row: dict) -> str:
    value = str(row.get("recommended_decision") or "OKÄNT").strip().upper()
    if value.startswith("KÖP"):
        return "KÖP"
    if value.startswith("KANSKE"):
        return "KANSKE"
    if value.startswith("AVSTÅ"):
        return "AVSTÅ"
    return value or "OKÄNT"


def _completed(rows: Iterable[dict]) -> list[dict]:
    return [r for r in rows if r.get("status") == "sålt" and _to_float(r.get("actual_net_profit")) is not None]


def _decision_summary(rows: list[dict]) -> list[dict]:
    out = []
    for decision in ("KÖP", "KANSKE", "AVSTÅ"):
        group = [r for r in rows if _decision(r) == decision]
        profits = [_to_float(r.get("actual_net_profit")) for r in group]
        profits = [x for x in profits if x is not None]
        wins = sum(1 for x in profits if x > 0)
        out.append({
            "decision": decision,
            "count": len(group),
            "profitable_count": wins,
            "profitable_rate_pct": round(wins / len(group) * 100, 1) if group else None,
            "median_actual_net_profit": round(median(profits), 2) if profits else None,
            "enough_for_pattern": len(group) >= MIN_SEGMENT_SAMPLE,
        })
    return out


def build_model_review_dashboard(entries: Iterable[dict]) -> dict[str, Any]:
    rows = list(entries)
    sold = _completed(rows)
    fp = build_false_positive_review(rows)
    fn = build_false_negative_review(rows)

    fp_by_key = {x["key"]: x for x in fp["segments"]}
    key_aliases = {
        "information_edge_candidate_at_capture": "information_edge",
        "hidden_find_candidate_at_capture": "hidden_find",
        "market_edge_candidate_at_capture": "market_edge",
        "mispriced_rookie_candidate_at_capture": "rookie_hunter",
    }
    fn_by_key = {key_aliases.get(x["key"], x["key"]): x for x in fn["segments"]}
    keys = sorted(set(fp_by_key) | set(fn_by_key))
    signal_rows = []
    for key in keys:
        a = fp_by_key.get(key)
        b = fn_by_key.get(key)
        label = (a or b or {}).get("label", key)
        buy_n = int((a or {}).get("eligible_count") or 0)
        fp_n = int((a or {}).get("false_positive_count") or 0)
        nonbuy_n = int((b or {}).get("eligible_count") or 0)
        fn_n = int((b or {}).get("false_negative_count") or 0)
        signal_rows.append({
            "key": key,
            "label": label,
            "completed_buy_count": buy_n,
            "false_positive_count": fp_n,
            "false_positive_rate_pct": (a or {}).get("false_positive_rate_pct"),
            "completed_non_buy_count": nonbuy_n,
            "false_negative_count": fn_n,
            "false_negative_rate_pct": (b or {}).get("false_negative_rate_pct"),
            "enough_buy_sample": buy_n >= MIN_SEGMENT_SAMPLE,
            "enough_non_buy_sample": nonbuy_n >= MIN_SEGMENT_SAMPLE,
            "reviewable": buy_n >= MIN_SEGMENT_SAMPLE or nonbuy_n >= MIN_SEGMENT_SAMPLE,
        })

    # Put the most decision-relevant, sufficiently sampled conflicts first.
    signal_rows.sort(
        key=lambda x: (
            x["reviewable"],
            (x["false_positive_rate_pct"] or 0) + (x["false_negative_rate_pct"] or 0),
            x["completed_buy_count"] + x["completed_non_buy_count"],
        ),
        reverse=True,
    )

    buy_reviewed = fp["completed_buy_recommendations"]
    fp_rate = fp.get("false_positive_rate_pct")
    buy_clean_rate = round(100 - fp_rate, 1) if fp_rate is not None else None

    readiness = "review_ready" if len(sold) >= MIN_MANUAL_REVIEW_SAMPLE else ("descriptive" if len(sold) >= 5 else "collecting")
    if not sold:
        readiness = "empty"

    return {
        "sold_count": len(sold),
        "readiness": readiness,
        "supports_manual_model_review": len(sold) >= MIN_MANUAL_REVIEW_SAMPLE,
        "min_manual_review_sample": MIN_MANUAL_REVIEW_SAMPLE,
        "completed_buy_recommendations": buy_reviewed,
        "buy_without_false_positive_rate_pct": buy_clean_rate,
        "false_positive_count": fp["false_positive_count"],
        "false_positive_rate_pct": fp_rate,
        "completed_non_buy_recommendations": fn["completed_non_buy_recommendations"],
        "false_negative_count": fn["false_negative_count"],
        "false_negative_rate_pct": fn.get("false_negative_rate_pct"),
        "decision_summary": _decision_summary(sold),
        "signals": signal_rows,
        "automatic_weight_changes": False,
        "note": (
            "Model Review bygger bara på verkligt avslutade affärer. Den jämför dåliga KÖP, "
            "missade starka vinnare och faktiskt utfall per beslut/signal. Historiska samband "
            "är inte bevisade orsaker och modellen ändrar aldrig vikter automatiskt."
        ),
    }
