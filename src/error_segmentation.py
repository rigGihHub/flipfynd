"""Segment prediction errors across completed Flip Journal trades.

The purpose is diagnostic: identify where FlipFynd tends to be too optimistic,
too conservative, or too slow/fast in its estimates. Missing historical fields
stay missing and are never backfilled.
"""
from __future__ import annotations
from statistics import median

MIN_SEGMENT_SAMPLE = 5

def _n(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def _completed(rows):
    return [
        r for r in (rows or [])
        if r.get("status") == "sålt" and _n(r.get("actual_net_profit")) is not None
    ]

def _bucket(value, cuts, labels):
    v = _n(value)
    if v is None:
        return None
    for cut, label in zip(cuts, labels):
        if v < cut:
            return label
    return labels[-1]

def _metric(rows, pred_key, actual_key):
    pairs = []
    for r in rows:
        p = _n(r.get(pred_key))
        a = _n(r.get(actual_key))
        if p is None or a is None:
            continue
        pairs.append(a - p)
    if not pairs:
        return {"count": 0, "median_error": None, "median_abs_error": None}
    return {
        "count": len(pairs),
        "median_error": round(median(pairs), 2),
        "median_abs_error": round(median([abs(x) for x in pairs]), 2),
    }

def _segment(rows, key, labeler):
    groups = {}
    for r in rows:
        label = labeler(r)
        if label in (None, "", "Okänd"):
            continue
        groups.setdefault(str(label), []).append(r)

    out = []
    for label, group in groups.items():
        profit = _metric(group, "expected_net_profit_at_capture", "actual_net_profit")
        roi = _metric(group, "expected_roi_pct_at_capture", "actual_roi_pct")
        days = _metric(group, "flip_velocity_days_at_capture", "days_to_sell")
        error_samples = max(profit["count"], roi["count"], days["count"])
        out.append({
            "segment": key,
            "label": label,
            "count": len(group),
            "profit": profit,
            "roi": roi,
            "days_to_sell": days,
            "enough": error_samples >= MIN_SEGMENT_SAMPLE,
        })
    return out

def build_error_segmentation(rows):
    sold = _completed(rows)

    defs = [
        ("sport", lambda r: r.get("sport")),
        ("price_band", lambda r: _bucket(r.get("purchase_price"), [100, 300, 750, 1500], ["<100 kr", "100–299 kr", "300–749 kr", "750–1499 kr", "1500+ kr"])),
        ("risk_band", lambda r: _bucket(r.get("risk_score_at_capture"), [35, 65, 101], ["Låg risk", "Medelrisk", "Hög risk"])),
        ("sellability_band", lambda r: _bucket(r.get("sellability_at_capture"), [40, 70, 101], ["Låg säljbarhet", "Medel", "Hög säljbarhet"])),
        ("valuation_confidence", lambda r: _bucket(r.get("valuation_confidence_at_capture"), [40, 70, 101], ["Låg säkerhet", "Medel", "Hög säkerhet"])),
        ("exact_comp", lambda r: "Exakt comp fanns" if r.get("exact_comp_available_at_capture") is True else ("Ingen exakt comp" if r.get("exact_comp_available_at_capture") is False else None)),
        ("rookie_signal", lambda r: "Rookie-signal" if r.get("mispriced_rookie_candidate_at_capture") is True else ("Ingen rookie-signal" if r.get("mispriced_rookie_candidate_at_capture") is False else None)),
        ("market_edge", lambda r: "Market Edge" if r.get("market_edge_candidate_at_capture") is True else ("Ingen Market Edge" if r.get("market_edge_candidate_at_capture") is False else None)),
        ("information_edge", lambda r: "Information Edge" if r.get("information_edge_candidate_at_capture") is True else ("Ingen Information Edge" if r.get("information_edge_candidate_at_capture") is False else None)),
    ]

    segments = []
    for key, labeler in defs:
        segments.extend(_segment(sold, key, labeler))

    reviewable = [s for s in segments if s["enough"]]

    # Never rank SEK, percentage points and days against each other.
    # Each metric gets its own dimensionally valid review order.
    reviewable_profit = sorted(
        [s for s in reviewable if s["profit"]["count"] >= MIN_SEGMENT_SAMPLE and s["profit"]["median_abs_error"] is not None],
        key=lambda s: (float(s["profit"]["median_abs_error"]), s["profit"]["count"], s["count"]),
        reverse=True,
    )
    reviewable_roi = sorted(
        [s for s in reviewable if s["roi"]["count"] >= MIN_SEGMENT_SAMPLE and s["roi"]["median_abs_error"] is not None],
        key=lambda s: (float(s["roi"]["median_abs_error"]), s["roi"]["count"], s["count"]),
        reverse=True,
    )
    reviewable_velocity = sorted(
        [s for s in reviewable if s["days_to_sell"]["count"] >= MIN_SEGMENT_SAMPLE and s["days_to_sell"]["median_abs_error"] is not None],
        key=lambda s: (float(s["days_to_sell"]["median_abs_error"]), s["days_to_sell"]["count"], s["count"]),
        reverse=True,
    )

    # Stable non-severity ordering for the generic diagnostic list.
    reviewable.sort(key=lambda s: (s["segment"], s["label"]))
    return {
        "sold_count": len(sold),
        "segments": segments,
        "reviewable": reviewable,
        "reviewable_count": len(reviewable),
        "reviewable_by_metric": {
            "profit": reviewable_profit,
            "roi": reviewable_roi,
            "velocity": reviewable_velocity,
        },
        "automatic_model_changes": False,
        "note": "Visar bara segment med verkliga avslut. Minst 5 jämförbara utfall krävs. Vinstfel (kr), ROI-fel (%-enheter) och säljtid (dagar) rangordnas separat och jämförs aldrig i en gemensam severity.",
    }
