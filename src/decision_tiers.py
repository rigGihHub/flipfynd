"""Novice-facing decision tiers.

Separates opportunity potential from evidence certainty so a speculative card
cannot visually resemble a verified buy.
"""
from __future__ import annotations


def _n(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _title(item):
    return str(item.get("titel") or item.get("title") or "Okänt kort")


def _url(item):
    return item.get("lank") or item.get("url")


def _certainty(item):
    for key in ("ranking_confidence_score","deal_confidence_score","confidence","valuation_confidence_score"):
        if item.get(key) is not None:
            return max(0.0,min(100.0,_n(item.get(key))))
    return 0.0


def _potential(item):
    # Existing deal score is used only as opportunity potential, never certainty.
    return max(0.0,min(100.0,_n(item.get("deal_score"))))


def _market_value(item):
    if item.get("valuation_display_safe") is not True:
        return None
    for key in ("market_value_estimate","expected_resale","estimated_market_value","marknadsvarde"):
        if item.get(key) is not None:
            return _n(item.get(key))
    return None


def _base_row(item):
    decision=str(item.get("beslut") or item.get("decision") or item.get("recommendation") or "EJ BESLUT").upper()
    sold=int(_n(item.get("sold_comparable_count"),0))
    identity_ok=bool(
        item.get("exact_identity_gate_supports_exact_comp_search")
        or item.get("exact_identity_gate_status") in {"READY","EXACT","STRONG"}
    )
    blockers=list(item.get("decision_diagnostics") or [])
    return {
        "title":_title(item),
        "url":_url(item),
        "decision":decision,
        "potential":_potential(item),
        "certainty":_certainty(item),
        "sold_comps":sold,
        "identity_ok":identity_ok,
        "market_value":_market_value(item),
        "total_cost":item.get("analysis_total_cost") if item.get("analysis_total_cost") is not None else item.get("total_cost"),
        "shipping":item.get("frakt"),
        "shipping_known":item.get("shipping_known"),
        "primary_blocker":blockers[0] if blockers else None,
    }


def build_decision_tiers(candidates, total_limit=3):
    rows=[_base_row(i) for i in (candidates or [])]
    for r in rows:
        is_buy=r["decision"].startswith("KÖP") or r["decision"].startswith("KOP")
        r["tier"]=(
            "VERIFIED"
            if is_buy and r["certainty"]>=60 and r["sold_comps"]>=2 and r["identity_ok"] and r["market_value"] is not None
            else "PROMISING"
            if r["potential"]>=55
            else "REMAINDER"
        )

    tier_order={"VERIFIED":2,"PROMISING":1,"REMAINDER":0}
    rows.sort(key=lambda r:(tier_order[r["tier"]],r["certainty"],r["potential"],r["sold_comps"]),reverse=True)

    selected=[]
    # Prefer one from each meaningful tier, then fill remaining by tier quality.
    for tier in ("VERIFIED","PROMISING","REMAINDER"):
        found=next((r for r in rows if r["tier"]==tier and r not in selected),None)
        if found and len(selected)<total_limit:
            selected.append(found)
    for r in rows:
        if len(selected)>=total_limit:
            break
        if r not in selected:
            selected.append(r)

    return {
        "rows":selected,
        "verified_count":sum(1 for r in rows if r["tier"]=="VERIFIED"),
        "promising_count":sum(1 for r in rows if r["tier"]=="PROMISING"),
        "creates_new_decision":False,
        "note":"Fyndpotential och säkerhet visas separat. Potential beskriver möjlighet; säkerhet beskriver evidensstyrka.",
    }
