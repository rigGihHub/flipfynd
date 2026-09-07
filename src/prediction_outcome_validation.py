from statistics import median
MIN_METRIC_SAMPLE=5
MIN_REVIEW_SAMPLE=20
def _n(v):
    if v in (None,""): return None
    try: return float(v)
    except (TypeError,ValueError): return None
def _metric(rows,pred,actual):
    pairs=[]
    for r in rows:
        p=_n(r.get(pred)); a=_n(r.get(actual))
        if p is not None and a is not None: pairs.append((p,a,a-p))
    if not pairs: return {"count":0,"median_error":None,"median_abs_error":None,"bias":"no_data","enough":False}
    e=[x[2] for x in pairs]; me=median(e)
    return {"count":len(pairs),"median_error":round(me,2),"median_abs_error":round(median([abs(x) for x in e]),2),
            "bias":"overestimated" if me<0 else ("underestimated" if me>0 else "balanced"),"enough":len(pairs)>=5}
def build_prediction_outcome_validation(rows):
    sold=[r for r in (rows or []) if r.get("status")=="sålt" and _n(r.get("actual_net_profit")) is not None]
    p=_metric(sold,"expected_net_profit_at_capture","actual_net_profit")
    roi=_metric(sold,"expected_roi_pct_at_capture","actual_roi_pct")
    days=_metric(sold,"flip_velocity_days_at_capture","days_to_sell")
    return {"sold_count":len(sold),"profit":p,"roi":roi,"days_to_sell":days,
            "review_ready":len(sold)>=20 and sum(x["enough"] for x in (p,roi,days))>=2,
            "automatic_model_changes":False,
            "note":"Fel = verkligt utfall minus prognos. Äldre poster utan sparad prognos räknas inte för det måttet."}
