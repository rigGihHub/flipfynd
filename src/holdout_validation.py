"""Holdout validation for proposed FlipFynd corrections.

Rows are split deterministically into discovery and holdout cohorts. The
correction is estimated only on discovery data and evaluated only on holdout
data. This is still observational validation, not a guarantee of future gains.
"""
from __future__ import annotations
from statistics import median

MIN_DISCOVERY=5
MIN_HOLDOUT=5
MIN_IMPROVEMENT_PCT=5.0

def _n(v):
    if v in (None,""): return None
    try: return float(v)
    except (TypeError,ValueError): return None

def _prediction_time(row):
    raw = row.get("prediction_timestamp_at_capture")
    if not raw:
        return None
    from datetime import datetime, timezone
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _split(rows):
    rows=list(rows or [])
    if len(rows)<MIN_DISCOVERY+MIN_HOLDOUT:
        return {"status":"INSUFFICIENT_DATA","discovery":[],"holdout":[],"missing_timestamp_count":0}

    stamped=[]
    missing=0
    for row in rows:
        ts=_prediction_time(row)
        if ts is None:
            missing += 1
            continue
        stamped.append((ts,row))

    # Fail closed: do not silently fall back to sale_date, updated_at, created_at or id.
    if missing:
        return {"status":"MISSING_DATES","discovery":[],"holdout":[],"missing_timestamp_count":missing}
    if len(stamped)<MIN_DISCOVERY+MIN_HOLDOUT:
        return {"status":"INSUFFICIENT_DATA","discovery":[],"holdout":[],"missing_timestamp_count":0}

    stamped.sort(key=lambda pair: pair[0])
    ordered=[row for _,row in stamped]
    cut=max(MIN_DISCOVERY, len(ordered)//2)
    if len(ordered)-cut < MIN_HOLDOUT:
        cut=len(ordered)-MIN_HOLDOUT
    return {"status":"READY","discovery":ordered[:cut],"holdout":ordered[cut:],"missing_timestamp_count":0}

def _matches(row, segment, label):
    if segment=="sport":
        return str(row.get("sport") or "")==label
    if segment=="exact_comp":
        value="Exakt comp fanns" if row.get("exact_comp_available_at_capture") is True else ("Ingen exakt comp" if row.get("exact_comp_available_at_capture") is False else None)
        return value==label
    if segment=="rookie_signal":
        value="Rookie-signal" if row.get("mispriced_rookie_candidate_at_capture") is True else ("Ingen rookie-signal" if row.get("mispriced_rookie_candidate_at_capture") is False else None)
        return value==label
    if segment=="market_edge":
        value="Market Edge" if row.get("market_edge_candidate_at_capture") is True else ("Ingen Market Edge" if row.get("market_edge_candidate_at_capture") is False else None)
        return value==label
    if segment=="information_edge":
        value="Information Edge" if row.get("information_edge_candidate_at_capture") is True else ("Ingen Information Edge" if row.get("information_edge_candidate_at_capture") is False else None)
        return value==label
    if segment=="price_band":
        p=_n(row.get("purchase_price"))
        if p is None: return False
        if p<100: v="<100 kr"
        elif p<300: v="100–299 kr"
        elif p<750: v="300–749 kr"
        elif p<1500: v="750–1499 kr"
        else: v="1500+ kr"
        return v==label
    if segment=="risk_band":
        v=_n(row.get("risk_score_at_capture"))
        if v is None: return False
        name="Låg risk" if v<35 else ("Medelrisk" if v<65 else "Hög risk")
        return name==label
    if segment=="sellability_band":
        v=_n(row.get("sellability_at_capture"))
        if v is None: return False
        name="Låg säljbarhet" if v<40 else ("Medel" if v<70 else "Hög säljbarhet")
        return name==label
    if segment=="valuation_confidence":
        v=_n(row.get("valuation_confidence_at_capture"))
        if v is None: return False
        name="Låg säkerhet" if v<40 else ("Medel" if v<70 else "Hög säkerhet")
        return name==label
    return False

def _pairs(rows,pred,actual):
    out=[]
    for r in rows:
        p=_n(r.get(pred)); a=_n(r.get(actual))
        if p is not None and a is not None: out.append((p,a))
    return out

def _mae(pairs, shift=0.0):
    if not pairs: return None
    return median([abs(a-(p+shift)) for p,a in pairs])

def _validate_metric(discovery,holdout,pred,actual):
    dp=_pairs(discovery,pred,actual)
    hp=_pairs(holdout,pred,actual)
    if len(dp)<MIN_DISCOVERY or len(hp)<MIN_HOLDOUT:
        return {"eligible":False,"discovery_count":len(dp),"holdout_count":len(hp)}
    shift=median([a-p for p,a in dp])
    before=_mae(hp,0.0); after=_mae(hp,shift)
    improvement=((before-after)/before*100) if before not in (None,0) else 0.0
    return {
        "eligible":True,"discovery_count":len(dp),"holdout_count":len(hp),
        "shift":round(shift,2),"mae_before":round(before,2),"mae_after":round(after,2),
        "improvement_pct":round(improvement,1),
        "passes":after<before and improvement>=MIN_IMPROVEMENT_PCT,
    }

def validate_candidate_holdout(rows,candidate):
    subset=[r for r in (rows or []) if r.get("status")=="sålt" and _matches(r,candidate.get("segment"),candidate.get("label"))]
    split=_split(subset)
    discovery=split["discovery"]
    holdout=split["holdout"]
    metrics={}
    for kind,_direction,_severity in candidate.get("signals",[]):
        if kind=="profit":
            metrics["profit"]=_validate_metric(discovery,holdout,"expected_net_profit_at_capture","actual_net_profit")
        elif kind=="roi":
            metrics["roi"]=_validate_metric(discovery,holdout,"expected_roi_pct_at_capture","actual_roi_pct")
        elif kind=="velocity":
            metrics["velocity"]=_validate_metric(discovery,holdout,"flip_velocity_days_at_capture","days_to_sell")
    eligible=[m for m in metrics.values() if m.get("eligible")]
    return {
        "segment":candidate.get("segment"),"label":candidate.get("label"),
        "temporal_status":split["status"],
        "missing_prediction_timestamp_count":split["missing_timestamp_count"],
        "discovery_count":len(discovery),"holdout_count":len(holdout),"metrics":metrics,
        "passes_holdout":split["status"]=="READY" and bool(eligible) and all(m.get("passes") for m in eligible),
        "automatic_change":False,
    }

def build_holdout_validation(rows,correction_review):
    results=[validate_candidate_holdout(rows,c) for c in (correction_review or {}).get("candidates",[])]
    passed=[r for r in results if r["passes_holdout"]]
    return {
        "tested_count":len(results),"passed_count":len(passed),
        "results":results,"passed":passed,"automatic_model_changes":False,
        "note":"Korrigeringen skattas på tidigare prediction_timestamp_at_capture och testas på senare prediction_timestamp_at_capture. Saknade prognostidpunkter ger avstående; sale_date, updated_at, created_at och id används aldrig som fallback.",
    }
