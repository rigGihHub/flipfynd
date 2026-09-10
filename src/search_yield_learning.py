"""Observe yield of Search Expansion routes without self-tuning decision logic."""
from collections import defaultdict

def _s(v): return str(v or "").strip()

def build_yield_report(items):
    groups=defaultdict(lambda:{"hits":0,"buy":0,"watch":0,"safe_value":0,"queries":set()})
    for item in items or []:
        if not isinstance(item,dict) or item.get("source_type")!="tradera_api_search_expansion": continue
        q=_s(item.get("search_expansion_query")); order=_s(item.get("search_expansion_order_by"))
        kind=_s(item.get("search_expansion_kind")) or "unknown"
        if not q or not order: continue
        g=groups[(kind,order)]; g["hits"]+=1; g["queries"].add(q.casefold())
        d=_s(item.get("beslut") or item.get("decision")).upper()
        if d=="KÖP": g["buy"]+=1
        elif d in {"BEVAKA","KANSKE"}: g["watch"]+=1
        if item.get("valuation_display_safe") is True: g["safe_value"]+=1
    rows=[]
    for (kind,order),g in groups.items():
        h=g["hits"]
        rows.append({"kind":kind,"order_by":order,"hits":h,"buy":g["buy"],"watch":g["watch"],
                     "safe_value":g["safe_value"],"query_count":len(g["queries"]),
                     "buy_rate_observed":round(g["buy"]/h*100,1) if h else None})
    rows.sort(key=lambda r:(r["buy"],r["watch"],r["safe_value"],r["hits"]),reverse=True)
    return {"rows":rows,"total_hits":sum(r["hits"] for r in rows),"route_count":len(rows),
            "can_change_buy_rules":False,"can_auto_tune":False}

def route_budget_guidance(report, minimum_hits=10):
    rows=[]
    for r in (report or {}).get("rows",[]):
        h=int(r.get("hits") or 0)
        if h<minimum_hits: status="OTILLRÄCKLIGT_UNDERLAG"
        elif int(r.get("buy") or 0)>0 or int(r.get("watch") or 0)>0: status="LOVANDE_OBSERVERAD"
        else: status="LÅG_YIELD_OBSERVERAD"
        rows.append({**r,"evidence_status":status})
    return {"rows":rows,"minimum_hits":minimum_hits,"changes_execution":False,"changes_buy_logic":False}
