"""Build one concise, fail-closed Best Buy decision card."""
from __future__ import annotations

from src.shipping_truth import resolve_shipping

def _n(v):
    if v in (None, ""): return None
    try: return float(v)
    except (TypeError, ValueError): return None

def _is_buy(item):
    decision=str(item.get("decision") or item.get("recommendation") or "").upper()
    return decision.startswith("KÖP") or decision.startswith("KOP")

def _identity_safe(item):
    return bool(item.get("exact_identity_gate_supports_dynamic_max_bid"))

def _verified_days(item):
    if item.get("flip_velocity_evidence") != "verified_sold_velocity":
        return None
    return _n(item.get("flip_velocity_expected_days"))

def _eligible(item):
    ce=item.get("capital_efficiency") or {}
    return (_is_buy(item) and _identity_safe(item) and ce.get("score") is not None and _n(item.get("analysis_total_cost") or item.get("total_cost")) not in (None,0) and _n(item.get("net_profit_estimate")) is not None)

def _stable_id(item):
    return str(item.get("lank") or item.get("url") or item.get("id") or item.get("titel") or "")

def build_best_buy_decision_card(candidates):
    eligible=[x for x in (candidates or []) if _eligible(x)]
    if not eligible:
        return {"status":"NO_SAFE_BUY","card":None,"note":"Ingen kandidat har just nu både KÖP-status, beslutsstark exakt identitet och tillräckligt underlag för ett tydligt förstaval."}
    def key(x):
        ce=x.get("capital_efficiency") or {}
        return (-(_n(ce.get("score")) or 0),-(_n(ce.get("profit_30d")) or 0),-(_n(x.get("net_profit_estimate")) or 0),str(x.get("titel") or ""),_stable_id(x))
    item=sorted(eligible,key=key)[0]
    ce=item.get("capital_efficiency") or {}
    days=_verified_days(item)
    shipping_info=resolve_shipping(item)
    return {"status":"READY","card":{
        "title":item.get("titel") or "Okänt kort","player_name":item.get("player_name"),
        "total_cost":_n(item.get("analysis_total_cost") or item.get("total_cost")),
        "expected_resale":_n(item.get("expected_resale")),"net_profit":_n(item.get("net_profit_estimate")),
        "floor_profit":_n(item.get("floor_profit_estimate")),"expected_days":days,"velocity_verified":days is not None,
        "max_total_price":_n(item.get("max_total_price")),"max_item_price":_n(item.get("max_item_price")),
        "shipping":shipping_info["shipping"],"shipping_known":shipping_info["known"],"shipping_label":shipping_info["label"],
        "capital_score":_n(ce.get("score")),"capital_label":ce.get("label") or "Ej bedömd",
        "sale_probability":_n(item.get("sale_probability")),"sold_comparable_count":int(item.get("sold_comparable_count") or 0),"sellability_label":item.get("liquidity_label") or item.get("sellability_label"),"sellability_score":_n(item.get("liquidity_score") or item.get("sellability_score")),"exact_identity_support":True,
        "exact_identity_status":item.get("exact_identity_gate_status") or "VERIFIERAD",
        "reasons":list(item.get("opportunity_reasons") or [])[:2],"url":item.get("lank")},
        "note":"Förstavalet rankas bara bland befintliga KÖP med beslutsstark exakt identitet och Capital Efficiency. Säljtid visas bara med verifierad sold-velocity."}
