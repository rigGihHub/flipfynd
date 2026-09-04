"""Conservative review of profitable deals that FlipFynd did not call KÖP.

Only completed real-world flips are eligible. This module is descriptive: it
does not infer causality and never changes model weights automatically.
"""
from __future__ import annotations

from statistics import median
from typing import Any, Iterable, Optional

MIN_PATTERN_SAMPLE = 5
MIN_SEGMENT_SAMPLE = 5
MIN_STRONG_PROFIT = 100.0
MIN_STRONG_ROI_PCT = 25.0

def _to_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _decision(row: dict) -> str:
    return str(row.get("recommended_decision") or "").strip().upper()

def _is_buy(row: dict) -> bool:
    return _decision(row).startswith("KÖP")

def _is_completed(row: dict) -> bool:
    return row.get("status") == "sålt" and _to_float(row.get("actual_net_profit")) is not None

def classify_false_negative(row: dict) -> dict[str, Any]:
    """Flag a strong completed winner that was not originally called KÖP."""
    if _is_buy(row) or not _is_completed(row):
        return {"eligible": False, "is_false_negative": False, "reasons": []}
    actual = _to_float(row.get("actual_net_profit"))
    purchase = _to_float(row.get("purchase_price"))
    roi = _to_float(row.get("actual_roi_pct"))
    if roi is None and purchase and purchase > 0 and actual is not None:
        roi = actual / purchase * 100
    strong = bool(actual is not None and actual >= MIN_STRONG_PROFIT and roi is not None and roi >= MIN_STRONG_ROI_PCT)
    reasons = ["strong_realized_winner"] if strong else []
    return {"eligible": True, "is_false_negative": strong, "reasons": reasons, "actual_net_profit": actual, "actual_roi_pct": roi}

def _bucket(value: Optional[float], cuts: tuple[float, float], labels: tuple[str, str, str]) -> Optional[str]:
    if value is None: return None
    if value < cuts[0]: return labels[0]
    if value < cuts[1]: return labels[1]
    return labels[2]

def _segment_memberships(row: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    decision = _decision(row) or "OKÄNT"
    out.append((f"decision:{decision}", f"Beslut: {decision}"))
    score = _to_float(row.get("deal_score_at_capture"))
    sb = _bucket(score, (70, 90), ("under70", "70-89", "90+"))
    if sb: out.append((f"score:{sb}", f"Fyndscore {sb}"))
    val = _to_float(row.get("valuation_confidence_at_capture"))
    vb = _bucket(val, (40, 60), ("low", "medium", "high"))
    if vb: out.append((f"valuation:{vb}", {"low":"Låg värderingssäkerhet", "medium":"Medel värderingssäkerhet", "high":"Hög värderingssäkerhet"}[vb]))
    risk = _to_float(row.get("risk_score_at_capture"))
    rb = _bucket(risk, (40, 70), ("low", "medium", "high"))
    if rb: out.append((f"risk:{rb}", {"low":"Låg risk", "medium":"Medelrisk", "high":"Hög risk"}[rb]))
    sell = _to_float(row.get("sellability_at_capture"))
    lb = _bucket(sell, (40, 70), ("low", "medium", "high"))
    if lb: out.append((f"sellability:{lb}", {"low":"Låg säljbarhet", "medium":"Medel säljbarhet", "high":"Hög säljbarhet"}[lb]))
    if row.get("decision_confidence_downgraded_at_capture"): out.append(("confidence_block", "Sänkt av säkerhetsgranskning"))
    if row.get("decision_conflict_downgraded_at_capture"): out.append(("conflict_block", "Sänkt av konfliktgranskning"))
    if row.get("exact_comp_available_at_capture") is False: out.append(("no_exact_comp", "Ingen verifierad sold comp"))
    for key, label in (("information_edge_candidate_at_capture","Informationsövertag"),("hidden_find_candidate_at_capture","Dolt fynd"),("market_edge_candidate_at_capture","Market Edge"),("mispriced_rookie_candidate_at_capture","Rookie Hunter")):
        if row.get(key): out.append((key, label))
    sport = str(row.get("sport") or "").strip().lower()
    if sport: out.append((f"sport:{sport}", f"Sport: {sport.capitalize()}"))
    return out

def build_false_negative_review(entries: Iterable[dict]) -> dict[str, Any]:
    rows = [r for r in entries if _is_completed(r) and not _is_buy(r)]
    classified = [(r, classify_false_negative(r)) for r in rows]
    misses = [(r, c) for r, c in classified if c["is_false_negative"]]
    segments: dict[str, dict[str, Any]] = {}
    for row, result in classified:
        for key, label in _segment_memberships(row):
            b = segments.setdefault(key, {"key":key,"label":label,"eligible":0,"missed":0,"profits":[]})
            b["eligible"] += 1
            profit = _to_float(row.get("actual_net_profit"))
            if profit is not None: b["profits"].append(profit)
            if result["is_false_negative"]: b["missed"] += 1
    segment_rows=[]
    for b in segments.values():
        n=b["eligible"]
        segment_rows.append({"key":b["key"],"label":b["label"],"eligible_count":n,"false_negative_count":b["missed"],"false_negative_rate_pct":round(b["missed"]/n*100,1) if n else None,"median_actual_net_profit":round(median(b["profits"]),2) if b["profits"] else None,"enough_for_pattern":n>=MIN_SEGMENT_SAMPLE})
    segment_rows.sort(key=lambda x:(x["enough_for_pattern"],x["false_negative_rate_pct"] or 0,x["eligible_count"]),reverse=True)
    count=len(misses); reviewed=len(rows)
    return {"completed_non_buy_recommendations":reviewed,"false_negative_count":count,"false_negative_rate_pct":round(count/reviewed*100,1) if reviewed else None,"supports_pattern_review":reviewed>=MIN_PATTERN_SAMPLE,"segments":segment_rows,"automatic_weight_changes":False,"thresholds":{"min_profit":MIN_STRONG_PROFIT,"min_roi_pct":MIN_STRONG_ROI_PCT},"note":"False Negative Review använder bara verkligt avslutade affärer som inte hade KÖP-rekommendation. Ett missat fynd kräver minst 100 kr faktisk nettovinst och minst 25 % faktisk ROI. Enstaka vinnare ändrar aldrig modellen automatiskt."}
