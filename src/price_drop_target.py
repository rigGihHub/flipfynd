"""Max-price target for candidates currently above the existing max total."""
def _n(v):
    if v in (None, ""): return None
    try: return float(v)
    except (TypeError, ValueError): return None

def build_price_drop_target(item, timing=None):
    timing=timing or {}
    if str(timing.get("action") or "")!="ÖVER MAXPRIS":
        return {"status":"NOT_APPLICABLE","note":"Maxprismål visas bara när aktuell kostnad ligger över befintligt maxpris."}
    max_total=_n(item.get("max_total_price"))
    shipping=_n(item.get("max_price_shipping_assumption"))
    if shipping is None: shipping=_n(item.get("frakt"))
    if max_total is None or max_total<=0:
        return {"status":"INSUFFICIENT_DATA","note":"Maxpris saknas."}
    target_total=round(max_total,2)
    target_item=round(max(0.0,target_total-shipping),2) if shipping is not None else None
    current_total=_n(item.get("analysis_total_cost") or item.get("total_cost"))
    drop_needed=round(max(0.0,current_total-target_total),2) if current_total is not None else None
    return {
        "status":"READY","target_total":target_total,"target_item_price":target_item,
        "shipping_assumption":shipping,"current_total":current_total,"drop_needed":drop_needed,
        "rule":"existing_max_total",
        "note":"Målet är exakt det befintliga maxpriset. Ingen extra säkerhetsmarginal hittas på i detta lager."
    }

def build_queue_price_drop_targets(queue,candidates,timing_rows):
    by_title={str(x.get("titel") or ""):x for x in (candidates or [])}
    timing_by_rank={r.get("rank"):r.get("timing") or {} for r in (timing_rows or [])}
    rows=[]
    for pick in (queue or {}).get("picks",[]):
        item=by_title.get(str(pick.get("title") or "")) or {}
        rows.append({"rank":pick.get("rank"),"title":pick.get("title"),
                     "target":build_price_drop_target(item,timing_by_rank.get(pick.get("rank"),{}))})
    return {"rows":rows}
