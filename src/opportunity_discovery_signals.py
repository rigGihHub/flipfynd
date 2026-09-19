"""Opportunity-first candidate routing.

Ten concrete discovery improvements are expressed as independent signals so
ranking can evolve without weakening the evidence gates.
"""
from __future__ import annotations


def _n(v, default=0.0):
    try: return float(v)
    except (TypeError, ValueError): return float(default)


def opportunity_discovery_signals(item):
    item = item or {}
    total = _n(item.get("analysis_total_cost") or item.get("total_cost") or item.get("pris"))
    signals = []
    def add(name, score, reason):
        signals.append({"name": name, "score": float(score), "reason": reason})

    # 1 freshness
    if item.get("latest_scan_at"): add("freshness", 4, "nyligen upptäckt")
    # 2 exact/search identity
    if item.get("exact_identity_gate_supports_comp_research"): add("identity", 8, "sökbar kortidentitet")
    # 3 active-price context
    ap=item.get("asking_price_opportunity") or {}
    if ap.get("possible_find"): add("active_margin", 14, "positiv marginal mot aktiva jämförpriser")
    # 4 verified sold evidence
    sold=int(_n(item.get("sold_comparable_count")))
    if sold: add("sold", min(18, sold*6), "verifierade avslut finns")
    # 5 underdescription/information edge
    if item.get("is_information_edge_candidate"): add("information_edge", 7, "möjligt informationsövertag")
    # 6 hidden find
    if item.get("is_hidden_find_candidate"): add("hidden_find", 6, "underexponerad annons")
    # 7 card-specific scarcity
    if item.get("valuable_card_tags") or _n(item.get("valuable_card_structure_score"))>0: add("card_merit", 7, "kortspecifik merit")
    # 8 demand, capped so fame cannot dominate economics
    demand=min(5, _n(item.get("player_card_demand_score"))/20)
    if demand>0: add("demand", demand, "efterfrågesignal")
    # 9 auction activity
    bids=int(_n(item.get("bid_count")))
    if bids>0: add("auction_activity", min(4,bids*.5), "budaktivitet")
    # 10 low-capital probe; intentionally tiny
    if 0<total<=75: add("capital_efficiency_probe", 2, "låg kapitalinsats")
    return signals


def opportunity_discovery_score(item):
    return round(sum(s["score"] for s in opportunity_discovery_signals(item)),2)
