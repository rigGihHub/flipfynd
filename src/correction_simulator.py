"""Evidence-based correction simulator for FlipFynd.

Tests candidate corrections against completed Flip Journal outcomes. The
simulator is descriptive only and never changes production predictions.
"""
from __future__ import annotations
from statistics import median

MIN_SAMPLE=5
MIN_IMPROVEMENT_PCT=5.0

def _n(v):
    if v in (None,""): return None
    try: return float(v)
    except (TypeError,ValueError): return None

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
        bands=[(100,"<100 kr"),(300,"100–299 kr"),(750,"300–749 kr"),(1500,"750–1499 kr")]
        for cut,name in bands:
            if p<cut: return name==label
        return label=="1500+ kr"
    if segment=="risk_band":
        v=_n(row.get("risk_score_at_capture"))
        if v is None: return False
        return ("Låg risk" if v<35 else ("Medelrisk" if v<65 else "Hög risk"))==label
    if segment=="sellability_band":
        v=_n(row.get("sellability_at_capture"))
        if v is None: return False
        return ("Låg säljbarhet" if v<40 else ("Medel" if v<70 else "Hög säljbarhet"))==label
    if segment=="valuation_confidence":
        v=_n(row.get("valuation_confidence_at_capture"))
        if v is None: return False
        return ("Låg säkerhet" if v<40 else ("Medel" if v<70 else "Hög säkerhet"))==label
    return False

def _mae(values):
    return median([abs(x) for x in values]) if values else None

def _simulate_metric(rows,pred_key,actual_key,shift):
    pairs=[]
    for r in rows:
        p=_n(r.get(pred_key)); a=_n(r.get(actual_key))
        if p is not None and a is not None:
            pairs.append((p,a))
    if len(pairs)<MIN_SAMPLE:
        return {"count":len(pairs),"eligible":False}
    before=[a-p for p,a in pairs]
    after=[a-(p+shift) for p,a in pairs]
    mae_before=_mae(before); mae_after=_mae(after)
    improvement=((mae_before-mae_after)/mae_before*100) if mae_before not in (None,0) else 0.0
    return {
        "count":len(pairs),"eligible":True,
        "shift":round(shift,2),
        "mae_before":round(mae_before,2),
        "mae_after":round(mae_after,2),
        "improvement_pct":round(improvement,1),
        "improves":improvement>=MIN_IMPROVEMENT_PCT and mae_after<mae_before,
    }

def simulate_correction(rows,candidate):
    segment=candidate.get("segment"); label=candidate.get("label")
    subset=[r for r in (rows or []) if r.get("status")=="sålt" and _matches(r,segment,label)]
    sims={}
    for kind,direction,_severity in candidate.get("signals",[]):
        if kind=="profit":
            vals=[]
            for r in subset:
                p=_n(r.get("expected_net_profit_at_capture")); a=_n(r.get("actual_net_profit"))
                if p is not None and a is not None: vals.append(a-p)
            shift=median(vals) if len(vals)>=MIN_SAMPLE else 0
            sims["profit"]=_simulate_metric(subset,"expected_net_profit_at_capture","actual_net_profit",shift)
        elif kind=="roi":
            vals=[]
            for r in subset:
                p=_n(r.get("expected_roi_pct_at_capture")); a=_n(r.get("actual_roi_pct"))
                if p is not None and a is not None: vals.append(a-p)
            shift=median(vals) if len(vals)>=MIN_SAMPLE else 0
            sims["roi"]=_simulate_metric(subset,"expected_roi_pct_at_capture","actual_roi_pct",shift)
        elif kind=="velocity":
            vals=[]
            for r in subset:
                p=_n(r.get("flip_velocity_days_at_capture")); a=_n(r.get("days_to_sell"))
                if p is not None and a is not None: vals.append(a-p)
            shift=median(vals) if len(vals)>=MIN_SAMPLE else 0
            sims["velocity"]=_simulate_metric(subset,"flip_velocity_days_at_capture","days_to_sell",shift)
    eligible=[x for x in sims.values() if x.get("eligible")]
    improved=[x for x in eligible if x.get("improves")]
    return {
        "segment":segment,"label":label,"count":len(subset),"metrics":sims,
        "worth_reviewing": bool(eligible) and len(improved)==len(eligible),
        "automatic_change":False,
    }

def build_correction_simulation(rows,correction_review):
    results=[simulate_correction(rows,c) for c in (correction_review or {}).get("candidates",[])]
    reviewable=[r for r in results if r["worth_reviewing"]]
    return {
        "tested_count":len(results),
        "passed_count":len(reviewable),
        "results":results,
        "reviewable":reviewable,
        "automatic_model_changes":False,
        "note":"Simulatorn testar medianbaserade korrigeringar på samma historiska segment. Resultatet är bara ett första filter och inte bevis för framtida förbättring.",
    }
