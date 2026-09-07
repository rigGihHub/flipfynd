"""Side-by-side decision comparison for the existing Top 3 Buy Queue.

This module never reranks candidates and never creates a new KÖP signal.
It exposes already-produced economics, capital use and sellability in a
consistent comparison surface.
"""
def _n(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def _sellability(item):
    score=_n(item.get("liquidity_score") or item.get("liquidity"))
    label=item.get("liquidity_label") or item.get("sellability_label")
    evidence=item.get("liquidity_evidence") or item.get("flip_velocity_evidence")
    return score,label,evidence

def build_top_buy_decision_compare(queue,candidates):
    by_title={str(x.get("titel") or ""):x for x in (candidates or [])}
    rows=[]
    for pick in (queue or {}).get("picks",[]):
        item=by_title.get(str(pick.get("title") or ""))
        if not item:
            continue
        total=_n(item.get("analysis_total_cost") or item.get("total_cost"))
        weak=_n(item.get("floor_profit_estimate"))
        likely=_n(item.get("net_profit_estimate"))
        if total in (None,0) or likely is None:
            continue
        score,label,evidence=_sellability(item)
        verified_days=_n(item.get("flip_velocity_expected_days")) if item.get("flip_velocity_evidence")=="verified_sold_velocity" else None
        ce=item.get("capital_efficiency") or {}
        turnover=None
        if verified_days is not None and verified_days > 0:
            cycles_30d=30.0/verified_days
            profit_30d=likely*cycles_30d
            roi_30d=(profit_30d/total)*100.0
            capital_days=total*verified_days
            profit_per_1000_capital_days=(likely/capital_days)*1000.0 if capital_days > 0 else None
            turnover={
                "verified":True,
                "expected_days":round(verified_days,1),
                "cycles_30d":round(cycles_30d,2),
                "profit_30d":round(profit_30d,1),
                "roi_30d_pct":round(roi_30d,1),
                "profit_per_1000_capital_days":round(profit_per_1000_capital_days,2) if profit_per_1000_capital_days is not None else None,
                "note":"Normaliserat på verifierad sold-velocity. Visar kapitalets förväntade omloppstakt, inte en garanti om återinvestering eller framtida försäljning."
            }
        rows.append({
            "rank":pick.get("rank"),
            "title":pick.get("title"),
            "capital_tied":round(total,2),
            "weak_profit":weak,
            "weak_roi_pct":round(weak/total*100,1) if weak is not None else None,
            "likely_profit":round(likely,2),
            "likely_roi_pct":round(likely/total*100,1),
            "sellability_score":score,
            "sellability_label":label,
            "sellability_evidence":evidence,
            "verified_sell_days":verified_days,
            "capital_efficiency_score":_n(ce.get("score") or item.get("capital_efficiency_score")),
            "profit_30d":_n(ce.get("profit_30d")),
            "turnover":turnover,
            "url":item.get("lank"),
        })
    return {
        "status":"READY" if rows else "INSUFFICIENT_DATA",
        "rows":rows,
        "ranking_changed":False,
        "note":"Jämförelsen behåller Top 3-köns befintliga ordning. Kapitalets omlopp normaliseras bara när säljtid har verifierad sold-velocity; annars avstår vyn. Inga nya köpsignaler skapas.",
    }
