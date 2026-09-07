"""Transparent comp evidence ladder for FlipFynd.

This module does not change valuation. It explains which observed comps are
eligible for valuation and which are only context or explicitly rejected.
"""
from __future__ import annotations


def _verified_player_only(rows):
    out=[]
    for row in rows or []:
        if not row.get("sold"):
            continue
        matches=set(row.get("matches") or [])
        if "spelare" in matches and len(matches) == 1:
            out.append(row)
    return out


def build_exact_evidence_ladder(exact_hunt: dict | None) -> dict:
    hunt=exact_hunt or {}
    exact=list(hunt.get("exact") or [])
    near=list(hunt.get("near") or [])
    weak=list(hunt.get("weak") or [])
    rejected=list(hunt.get("rejected") or [])
    player_only=_verified_player_only(weak)
    insufficient=[r for r in weak if r not in player_only]

    levels=[
        {
            "key":"EXACT",
            "label":"Exact",
            "count":len(exact),
            "valuation_eligible":True,
            "meaning":"Verifierad försäljning av samma kortidentitet enligt kända fält.",
        },
        {
            "key":"NEAR",
            "label":"Near",
            "count":len(near),
            "valuation_eligible":False,
            "meaning":"Närliggande verifierad försäljning, men minst ett identitetsfält saknas eller avviker i precision.",
        },
        {
            "key":"PLAYER_ONLY",
            "label":"Player-only",
            "count":len(player_only),
            "valuation_eligible":False,
            "meaning":"Samma spelare men inte tillräckligt stöd för samma kort/variant.",
        },
        {
            "key":"INSUFFICIENT",
            "label":"Otillräcklig",
            "count":len(insufficient),
            "valuation_eligible":False,
            "meaning":"För lite identitetsstöd för relevant comp-jämförelse.",
        },
        {
            "key":"REJECTED",
            "label":"Rejected",
            "count":len(rejected),
            "valuation_eligible":False,
            "meaning":"Identitetskonflikt gör posten olämplig som comp.",
        },
    ]
    return {
        "status":"READY" if hunt.get("unlocked") else "LOCKED",
        "levels":levels,
        "valuation_basis_count":len(exact),
        "valuation_basis":"EXACT_VERIFIED_SOLD_ONLY",
        "player_only":player_only,
        "insufficient":insufficient,
        "note":"Endast verifierade Exact-comps är värderingsgrund. Near och Player-only är endast kontext.",
    }


def build_premium_evidence_ladder(premium_hunt: dict | None) -> dict:
    hunt=premium_hunt or {}
    exact=list(hunt.get("exact") or [])
    near=list(hunt.get("near") or [])
    rejected=list(hunt.get("rejected") or [])
    insufficient_count=int(hunt.get("insufficient_count", 0) or 0)
    levels=[
        {
            "key":"EXACT_PREMIUM",
            "label":"Exact premium",
            "count":len(exact),
            "valuation_eligible":True,
            "meaning":"Verifierad försäljning av samma premiumidentitet.",
        },
        {
            "key":"NEAR_PREMIUM",
            "label":"Near premium",
            "count":len(near),
            "valuation_eligible":False,
            "meaning":"Liknande premiumkort men inte exakt samma kända identitet.",
        },
        {
            "key":"INSUFFICIENT",
            "label":"Otillräcklig",
            "count":insufficient_count,
            "valuation_eligible":False,
            "meaning":"För lite premiumidentitetsstöd.",
        },
        {
            "key":"REJECTED",
            "label":"Rejected",
            "count":len(rejected),
            "valuation_eligible":False,
            "meaning":"Konflikt i variant, numrering, auto/patch, set eller annan känd identitet.",
        },
    ]
    return {
        "status":"READY" if hunt.get("active") else "INACTIVE",
        "levels":levels,
        "valuation_basis_count":len(exact),
        "valuation_basis":"EXACT_PREMIUM_VERIFIED_SOLD_ONLY",
        "safe_for_valuation":bool(hunt.get("safe_for_valuation")),
        "note":"Premiumvärdering får endast bygga på verifierade Exact premium-comps; Near är kontext.",
    }
