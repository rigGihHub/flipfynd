"""Descriptive watch ordering for candidates above existing max price."""
def _n(v):
    if v in (None, ""): return None
    try: return float(v)
    except (TypeError, ValueError): return None

def build_watch_priority(item,timing=None,gap=None):
    timing=timing or {}; gap=gap or {}
    if str(timing.get("action") or "")!="ÖVER MAXPRIS":
        return {"status":"NOT_APPLICABLE"}
    gap_kr=_n(gap.get("gap_kr")); gap_pct=_n(gap.get("gap_pct"))
    if gap_kr is None:
        return {"status":"INSUFFICIENT_DATA"}
    return {
        "status":"READY","gap_kr":round(gap_kr,2),
        "gap_pct":round(gap_pct,1) if gap_pct is not None else None,
        "label":"Bevaka – närmast maxpris",
        "note":"Bevakningsordningen bygger endast på faktiskt avstånd till befintligt maxpris. Ingen sammanslagen score, ROI-vikt, CE-vikt eller godtycklig prioritetströskel används."
    }

def build_watch_priority_queue(queue,candidates,timing_rows,gap_rows):
    by_title={str(x.get("titel") or ""):x for x in (candidates or [])}
    tm={r.get("rank"):r.get("timing") or {} for r in (timing_rows or [])}
    gp={r.get("rank"):r.get("gap") or {} for r in (gap_rows or [])}
    rows=[]
    for p in (queue or {}).get("picks",[]):
        rank=p.get("rank"); item=by_title.get(str(p.get("title") or "")) or {}
        watch=build_watch_priority(item,tm.get(rank,{}),gp.get(rank,{}))
        rows.append({"rank":rank,"title":p.get("title"),"watch":watch,"url":item.get("lank")})
    ready=[r for r in rows if r["watch"].get("status")=="READY"]
    ready.sort(key=lambda r:(r["watch"]["gap_kr"], r["watch"].get("gap_pct") if r["watch"].get("gap_pct") is not None else 999, str(r["title"])))
    for i,r in enumerate(ready,1): r["watch"]["watch_rank"]=i
    return {"rows":rows,"ready":ready}
