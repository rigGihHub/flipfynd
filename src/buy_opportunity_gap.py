def _n(v):
    if v in (None,""): return None
    try: return float(v)
    except (TypeError,ValueError): return None

def build_opportunity_gap(item,timing=None,target=None):
    timing=timing or {}; target=target or {}
    if str(timing.get("action") or "")!="ÖVER MAXPRIS":
        return {"status":"NOT_APPLICABLE"}
    cur=_n(item.get("analysis_total_cost") or item.get("total_cost"))
    tgt=_n(target.get("target_total"))
    if cur is None or tgt is None or tgt<=0: return {"status":"INSUFFICIENT_DATA"}
    gap=max(0.0,cur-tgt); pct=(gap/cur*100) if cur>0 else None
    return {
        "status":"READY","gap_kr":round(gap,2),
        "gap_pct":round(pct,1) if pct is not None else None,
        "target_total":round(tgt,2),
        "note":"Visar exakt avstånd till befintligt maxpris. Inga godtyckliga nära/långt-band används."
    }

def build_queue_opportunity_gaps(queue,candidates,timing_rows,target_rows):
    bt={str(x.get("titel") or ""):x for x in (candidates or [])}
    tm={r.get("rank"):r.get("timing") or {} for r in (timing_rows or [])}
    tg={r.get("rank"):r.get("target") or {} for r in (target_rows or [])}
    rows=[]
    for p in (queue or {}).get("picks",[]):
        rank=p.get("rank"); g=build_opportunity_gap(bt.get(str(p.get("title") or "")) or {},tm.get(rank,{}),tg.get(rank,{}))
        rows.append({"rank":rank,"title":p.get("title"),"gap":g})
    ready=sorted([r for r in rows if r["gap"].get("status")=="READY"],key=lambda r:(r["gap"]["gap_kr"],r["gap"].get("gap_pct") or 999,str(r.get("title") or "")))
    for i,r in enumerate(ready,1): r["gap"]["wait_rank"]=i
    return {"rows":rows}
