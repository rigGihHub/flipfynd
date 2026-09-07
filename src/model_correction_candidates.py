"""Generate manual model-correction candidates from real outcome errors.

Suggestions are evidence notes only. They never alter production valuation,
ranking, decisions, or weights.
"""
from __future__ import annotations
MIN_SEGMENT_SAMPLE=5
STRONG_SAMPLE=10

def _candidate(seg):
    if not seg.get("enough") or seg.get("count",0) < MIN_SEGMENT_SAMPLE:
        return None
    profit=seg.get("profit") or {}
    roi=seg.get("roi") or {}
    days=seg.get("days_to_sell") or {}
    signals=[]
    if profit.get("count",0)>=MIN_SEGMENT_SAMPLE and profit.get("median_error") is not None:
        e=float(profit["median_error"])
        if e <= -25: signals.append(("profit","optimistic",abs(e)))
        elif e >= 25: signals.append(("profit","conservative",abs(e)))
    if roi.get("count",0)>=MIN_SEGMENT_SAMPLE and roi.get("median_error") is not None:
        e=float(roi["median_error"])
        if e <= -10: signals.append(("roi","optimistic",abs(e)))
        elif e >= 10: signals.append(("roi","conservative",abs(e)))
    if days.get("count",0)>=MIN_SEGMENT_SAMPLE and days.get("median_error") is not None:
        e=float(days["median_error"])
        if e >= 7: signals.append(("velocity","too_fast",abs(e)))
        elif e <= -7: signals.append(("velocity","too_slow",abs(e)))
    if not signals: return None

    strength="Stark kandidat" if seg.get("count",0)>=STRONG_SAMPLE and len(signals)>=2 else "Kandidat"
    actions=[]
    kinds={(a,b) for a,b,_ in signals}
    if ("profit","optimistic") in kinds or ("roi","optimistic") in kinds:
        actions.append("granska om värdering/vinst bör justeras ned")
    if ("profit","conservative") in kinds or ("roi","conservative") in kinds:
        actions.append("granska om modellen är onödigt försiktig")
    if ("velocity","too_fast") in kinds:
        actions.append("granska om förväntad säljtid bör höjas")
    if ("velocity","too_slow") in kinds:
        actions.append("granska om förväntad säljtid bör sänkas")
    return {
        "segment":seg["segment"],"label":seg["label"],"count":seg["count"],
        "strength":strength,"signals":signals,
        "metric_errors":{
            "profit_kr": next((round(x[2],1) for x in signals if x[0]=="profit"), None),
            "roi_percentage_points": next((round(x[2],1) for x in signals if x[0]=="roi"), None),
            "velocity_days": next((round(x[2],1) for x in signals if x[0]=="velocity"), None),
        },
        "suggestion":"; ".join(actions),
        "automatic_change":False,
    }

def build_model_correction_candidates(error_segmentation):
    candidates=[]
    for seg in (error_segmentation or {}).get("reviewable",[]):
        c=_candidate(seg)
        if c: candidates.append(c)
    candidates.sort(
        key=lambda x:(x["strength"]=="Stark kandidat", x["count"], x["segment"], x["label"]),
        reverse=True,
    )
    return {
        "count":len(candidates),
        "strong_count":sum(1 for x in candidates if x["strength"]=="Stark kandidat"),
        "candidates":candidates,
        "automatic_model_changes":False,
        "note":"Förslagen bygger på verkliga utfall men är endast kandidater för manuell granskning. Fel i kr, %-enheter och dagar hålls separata; ingen gemensam severity beräknas. Ingen haircut, vikt eller prognos ändras automatiskt.",
    }
