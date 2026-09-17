"""Collector-merit gate for Seller Top 5 presentation and deep selection.

This is a research-routing layer, never valuation or SOLD evidence.
"""
from __future__ import annotations

import re

from src.seller_collector_signals import collector_signals
from src.card_listing_integrity import assess_listing_integrity

_MASS_MARKET = re.compile(r"\b(match\s*attax|adrenalyn(?:\s*xl)?|sticker)\b", re.I)
_FAUX_PREMIUM = re.compile(r"\b(signature\s*style|silver\s*script|facsimile(?:\s*signature)?|printed\s*signature|pre[- ]?printed\s*signature)\b", re.I)
_TEAM_BADGE = re.compile(r"\b(team\s*badge|club\s*badge|team\s*crest|club\s*crest|club\s*logo|lagmärke|klubbmärke)\b", re.I)
_ROOKIE_WORD = re.compile(r"\b(rookie|rc)\b", re.I)
_STRONG_SIGNALS = {
    "one_of_one", "serial_numbered", "autograph", "patch_relic", "case_hit_ssp",
    "premium_insert", "premium_parallel", "error_variation", "short_print",
    "printing_plate", "buyback", "photo_variation", "football_named_chase",
    "flagship_rookie_variant", "upper_deck_day_with_cup", "upper_deck_population_count",
    "upper_deck_program_of_excellence", "named_chase_insert", "elite_parallel",
    "premium_autograph_structure", "premium_relic_structure", "premium_issue_variant",
}


def _num(value, default=0.0):
    try: return float(value)
    except (TypeError, ValueError): return float(default)


def assess_seller_card_merit(row: dict) -> dict:
    source=row.get("source_item") or row; title=str(source.get("titel") or source.get("title") or row.get("title") or "")
    collector=collector_signals(source); signals=set(collector.get("signals") or []); strong=sorted(signals & _STRONG_SIGNALS)
    sold=int(_num(row.get("sold_comps") or row.get("sold_comparable_count"))); identity_ok=bool(row.get("identity_ok") or row.get("exact_identity_gate_supports_exact_comp_search")); decision=str(row.get("decision") or row.get("beslut") or "SKIP").upper()
    market_value=_num(row.get("market_value") or row.get("estimated_market_value") or row.get("market_value_estimate"),0)
    profit=_num(row.get("risk_adjusted_profit") or row.get("net_profit_estimate") or row.get("net_profit"),0)
    mass_market_base=bool(_MASS_MARKET.search(title)) and not strong; mass_market_team_badge=bool(_MASS_MARKET.search(title) and _TEAM_BADGE.search(title)); faux_premium=bool(_FAUX_PREMIUM.search(title)); generic_rookie=bool(_ROOKIE_WORD.search(title)) and not strong and sold == 0
    # Base-like means there is no card-specific scarcity/premium trait. A star
    # name may make it collectible, but without SOLD/value/profit evidence that
    # is not a FlipFynd resale thesis.
    unsupported_base_like=not strong and sold==0 and market_value<=0 and profit<=0
    integrity=assess_listing_integrity(title)
    score=_num(collector.get("score"))+min(24,sold*8)+(6 if identity_ok else 0)+(12 if decision.startswith("KÖP") else 6 if decision.startswith("UNDERSÖK") else 0)
    if mass_market_base: score-=30
    if mass_market_team_badge and not (identity_ok and sold>=2): score-=35
    if faux_premium: score-=20
    if generic_rookie: score-=35
    if unsupported_base_like: score=min(score,15)
    if integrity["hard_exclusion_reasons"]: score=0
    elif integrity["reprint_risk"] and not (identity_ok and sold>=1): score-=25
    score=max(0.0,min(100.0,score))
    team_badge_evidence_ok=not mass_market_team_badge or (identity_ok and sold>=2)
    eligible=integrity["eligible_physical_single_card"] and team_badge_evidence_ok and (
        decision.startswith(("KÖP","UNDERSÖK")) or (bool(strong) and score>=18 and not faux_premium)
        or (score>=25 and not mass_market_base and not faux_premium and not generic_rookie and not unsupported_base_like)
        or (identity_ok and sold>=1 and not mass_market_base)
    )
    reasons=[]
    if mass_market_base: reasons.append("massproducerad lågprisprodukt utan verifierad variant")
    if mass_market_team_badge and not team_badge_evidence_ok: reasons.append("massproducerat lagmärke kräver exakt identitet och minst två SOLD-comps")
    if faux_premium: reasons.append("produktnamn/tryckt signatur är inte autograf")
    if generic_rookie: reasons.append("rookie/RC utan exakt SOLD eller verifierad premiumvariant är bara researchsignal")
    if unsupported_base_like: reasons.append("base-liknande kort utan SOLD, marknadsvärde eller positiv nettovinst får inte rankas på spelarnamn ensam")
    if integrity["hard_exclusion_reasons"]: reasons.append("inte ett verifierbart, fysiskt singelkort")
    if integrity["reprint_risk"]: reasons.append("nytryck/reproduktion kräver egna exakta jämförelseförsäljningar")
    if strong: reasons.append("kortspecifik signal: "+", ".join(strong))
    if sold: reasons.append(f"{sold} SOLD-comps")
    return {"score":round(score,1),"eligible":bool(eligible),"mass_market_base":mass_market_base,"mass_market_team_badge":mass_market_team_badge,"faux_premium":faux_premium,"generic_rookie_without_sales":generic_rookie,"unsupported_base_like":unsupported_base_like,"strong_signals":strong,"integrity":integrity,"reasons":reasons}
