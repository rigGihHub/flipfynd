"""Threshold-free timing description for already-approved buy candidates.

This layer never upgrades a decision. It only compares current total cost with the
existing max_total_price produced upstream.
"""
def _n(v):
    if v in (None,""): return None
    try: return float(v)
    except (TypeError,ValueError): return None

def build_buy_timing(item):
    decision=str(item.get("decision") or item.get("recommendation") or "").upper()
    if not (decision.startswith("KÖP") or decision.startswith("KOP")):
        return {"status":"NOT_BUY","action":"BEVAKA","note":"Kortet är inte ett befintligt KÖP-beslut."}
    total=_n(item.get("analysis_total_cost") or item.get("total_cost"))
    max_total=_n(item.get("max_total_price"))
    if total is None or max_total is None or max_total<=0:
        return {"status":"INSUFFICIENT_DATA","action":"BEVAKA","note":"Maxpris eller totalkostnad saknas."}
    margin=max_total-total
    margin_pct=(margin/max_total)*100
    if total <= max_total:
        action="INOM MAXPRIS"
        reason=f"Nuvarande totalpris ligger {margin:.0f} kr inom befintligt maxpris."
    else:
        action="ÖVER MAXPRIS"
        reason=f"Nuvarande totalpris ligger {abs(margin):.0f} kr över befintligt maxpris."
    return {
        "status":"READY","action":action,"total_cost":total,"max_total":max_total,
        "margin_kr":round(margin,2),"margin_pct":round(margin_pct,1),
        "reason":reason,
        "note":"Deskriptivt timinglager: jämför endast befintligt KÖP-beslut, aktuell totalkostnad och befintligt maxpris. Ingen extra 90%-regel, risktröskel eller confidence-tröskel används."
    }

def build_queue_buy_timing(queue,candidates):
    by_title={str(x.get("titel") or ""):x for x in (candidates or [])}
    return {"rows":[{"rank":p.get("rank"),"title":p.get("title"),"timing":build_buy_timing(by_title.get(str(p.get("title") or "")) or {})} for p in (queue or {}).get("picks",[])]}
