"""Rank up to three already-approved buys by capital efficiency."""
def _n(v):
    if v in (None,""): return None
    try: return float(v)
    except (TypeError,ValueError): return None
def _identity_safe(x): return bool(x.get("exact_identity_gate_supports_dynamic_max_bid"))
def _verified_days(x):
    return _n(x.get("flip_velocity_expected_days")) if x.get("flip_velocity_evidence")=="verified_sold_velocity" else None
def _eligible(x):
    d=str(x.get("decision") or x.get("recommendation") or "").upper(); ce=x.get("capital_efficiency") or {}
    return (d.startswith("KÖP") or d.startswith("KOP")) and _identity_safe(x) and _n(ce.get("score")) is not None and _n(x.get("analysis_total_cost") or x.get("total_cost")) not in (None,0) and _n(x.get("net_profit_estimate")) is not None
def _stable(x): return str(x.get("lank") or x.get("url") or x.get("id") or x.get("titel") or "")
def _key(x):
    ce=x.get("capital_efficiency") or {}
    return (-(_n(ce.get("score")) or 0),-(_n(ce.get("profit_30d")) or 0),-(_n(x.get("net_profit_estimate")) or 0),str(x.get("titel") or ""),_stable(x))
def build_top_buy_queue(candidates,limit=3):
    ranked=sorted([x for x in (candidates or []) if _eligible(x)],key=_key)[:max(1,int(limit))]
    picks=[]
    for i,x in enumerate(ranked):
        ce=x.get("capital_efficiency") or {}; nxt=ranked[i+1] if i+1<len(ranked) else None; why=[]
        if nxt:
            ne=nxt.get("capital_efficiency") or {}
            if (_n(ce.get("score")) or 0)>(_n(ne.get("score")) or 0): why.append(f"högre kapitalpoäng ({_n(ce.get('score')):.0f} mot {_n(ne.get('score')):.0f})")
            cp,np=_n(ce.get("profit_30d")),_n(ne.get("profit_30d"))
            if cp is not None and np is not None and cp>np: why.append(f"bättre vinsttakt ({cp:.0f} mot {np:.0f} kr/30 d)")
            cd,nd=_verified_days(x),_verified_days(nxt)
            if cd is not None and nd is not None and cd<nd: why.append(f"snabbare verifierad försäljning ({cd:.0f} mot {nd:.0f} dagar)")
        days=_verified_days(x)
        picks.append({"rank":i+1,"title":x.get("titel") or "Okänt kort","total_cost":_n(x.get("analysis_total_cost") or x.get("total_cost")),"net_profit":_n(x.get("net_profit_estimate")),"floor_profit":_n(x.get("floor_profit_estimate")),"expected_days":days,"velocity_verified":days is not None,"max_total_price":_n(x.get("max_total_price")),"capital_score":_n(ce.get("score")),"profit_30d":_n(ce.get("profit_30d")),"exact_identity_support":True,"why_ahead":why[:2],"url":x.get("lank")})
    return {"status":"READY" if picks else "NO_SAFE_BUYS","picks":picks,"note":"Kön innehåller bara befintliga KÖP med beslutsstark exakt identitet och Capital Efficiency. Säljtid används bara när sold-velocity är verifierad."}
