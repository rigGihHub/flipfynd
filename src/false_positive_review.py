"""Conservative review of false-positive buy recommendations.

A false positive is only counted after a completed real-world flip. The module
never infers a bad recommendation from an unsold listing and never changes
model weights automatically.
"""
from __future__ import annotations

from statistics import median
from typing import Any, Iterable, Optional

MIN_PATTERN_SAMPLE = 5
MIN_SEGMENT_SAMPLE = 5


def _to_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_buy(row: dict) -> bool:
    return str(row.get("recommended_decision") or "").strip().upper().startswith("KÖP")


def _is_completed(row: dict) -> bool:
    return row.get("status") == "sålt" and _to_float(row.get("actual_net_profit")) is not None


def classify_false_positive(row: dict) -> dict[str, Any]:
    """Classify one completed KÖP recommendation without inventing causality."""
    if not _is_buy(row) or not _is_completed(row):
        return {"eligible": False, "is_false_positive": False, "reasons": []}

    actual = _to_float(row.get("actual_net_profit"))
    expected = _to_float(row.get("expected_net_profit_at_capture"))
    reasons: list[str] = []

    if actual is not None and actual <= 0:
        reasons.append("actual_loss")

    # Large forecast miss is descriptive evidence of a false-positive buy call,
    # but small normal variation is deliberately ignored.
    if actual is not None and expected is not None and expected > 0:
        shortfall = expected - actual
        if shortfall >= max(50.0, expected * 0.50):
            reasons.append("large_profit_shortfall")

    return {
        "eligible": True,
        "is_false_positive": bool(reasons),
        "reasons": reasons,
        "actual_net_profit": actual,
        "expected_net_profit": expected,
    }


def _segment_memberships(row: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    score = _to_float(row.get("deal_score_at_capture"))
    if score is not None:
        if score >= 90:
            out.append(("score:90+", "Fyndscore 90+"))
        elif score >= 80:
            out.append(("score:80-89", "Fyndscore 80–89"))
        elif score >= 70:
            out.append(("score:70-79", "Fyndscore 70–79"))
        else:
            out.append(("score:<70", "Fyndscore under 70"))
    if row.get("information_edge_candidate_at_capture"):
        out.append(("information_edge", "Informationsövertag"))
    if row.get("hidden_find_candidate_at_capture"):
        out.append(("hidden_find", "Dolt fynd"))
    if row.get("market_edge_candidate_at_capture"):
        out.append(("market_edge", "Market Edge"))
    if row.get("mispriced_rookie_candidate_at_capture"):
        out.append(("rookie_hunter", "Rookie Hunter"))
    if row.get("misclassified_card_candidate_at_capture"):
        out.append(("misclassified", "Misclassified Hunter"))
    sport = str(row.get("sport") or "").strip().lower()
    if sport:
        out.append((f"sport:{sport}", f"Sport: {sport.capitalize()}"))
    return out


def build_false_positive_review(entries: Iterable[dict]) -> dict[str, Any]:
    buy_rows = [row for row in entries if _is_buy(row) and _is_completed(row)]
    classified = [(row, classify_false_positive(row)) for row in buy_rows]
    false_rows = [(row, result) for row, result in classified if result["is_false_positive"]]

    segments: dict[str, dict[str, Any]] = {}
    for row, result in classified:
        for key, label in _segment_memberships(row):
            bucket = segments.setdefault(key, {"key": key, "label": label, "eligible": 0, "false": 0, "profits": []})
            bucket["eligible"] += 1
            profit = _to_float(row.get("actual_net_profit"))
            if profit is not None:
                bucket["profits"].append(profit)
            if result["is_false_positive"]:
                bucket["false"] += 1

    segment_rows = []
    for bucket in segments.values():
        eligible = bucket["eligible"]
        segment_rows.append({
            "key": bucket["key"],
            "label": bucket["label"],
            "eligible_count": eligible,
            "false_positive_count": bucket["false"],
            "false_positive_rate_pct": round(bucket["false"] / eligible * 100, 1) if eligible else None,
            "median_actual_net_profit": round(median(bucket["profits"]), 2) if bucket["profits"] else None,
            "enough_for_pattern": eligible >= MIN_SEGMENT_SAMPLE,
        })
    segment_rows.sort(key=lambda x: (x["enough_for_pattern"], x["false_positive_rate_pct"] or 0, x["eligible_count"]), reverse=True)

    reason_counts: dict[str, int] = {"actual_loss": 0, "large_profit_shortfall": 0}
    for _, result in false_rows:
        for reason in result["reasons"]:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    reviewed = len(buy_rows)
    false_count = len(false_rows)
    return {
        "completed_buy_recommendations": reviewed,
        "false_positive_count": false_count,
        "false_positive_rate_pct": round(false_count / reviewed * 100, 1) if reviewed else None,
        "supports_pattern_review": reviewed >= MIN_PATTERN_SAMPLE,
        "reason_counts": reason_counts,
        "segments": segment_rows,
        "automatic_weight_changes": False,
        "note": (
            "False Positive Review använder bara verkligt avslutade affärer som hade KÖP-rekommendation. "
            "Förlust eller en stor dokumenterad vinstmiss kan markeras som falskt positivt utfall. "
            "Det visar var modellen bör granskas, inte varför utfallet blev dåligt, och ändrar inga vikter automatiskt."
        ),
    }
