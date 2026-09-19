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

    # 11 seller concentration / combined shipping opportunity
    seller = item.get("saljare") or item.get("seller")
    if seller and item.get("same_seller_opportunity"): add("same_seller", 3, "möjlig samfraktsfördel")
    # 12 grade clarity
    if item.get("grade") or item.get("grading_company"): add("grade_clarity", 3, "graderat kort är lättare att jämföra exakt")
    # 13 serial-number clarity
    if item.get("serial_denominator") or item.get("serial_number"): add("serial_clarity", 4, "numrering ger starkare kortidentitet")
    # 14 autograph/relic evidence, card-specific not checkbox-driven
    if item.get("is_auto") or item.get("autograph_evidence"): add("autograph", 4, "autografidentifiering")
    if item.get("is_patch") or item.get("is_relic") or item.get("relic_evidence"): add("relic", 3, "patch/relic-identifiering")
    # 15 listing-detail enrichment
    if item.get("detail_enrichment_status") == "ok": add("detail_enriched", 3, "annonsdetaljer verifierade")
    # 16 exact card number
    identity=item.get("exact_identity_gate_research_identity_fields") or item.get("exact_identity_gate_identity_fields") or {}
    if identity.get("card_number"): add("card_number", 4, "kortnummer identifierat")
    # 17 set+season completeness
    if identity.get("set_name") and identity.get("season"): add("set_season", 4, "set och säsong identifierade")
    # 18 price-context breadth
    asking=item.get("asking_price_opportunity") or {}
    comps=int(_n(asking.get("comparison_count")))
    if comps>=3: add("price_breadth", min(7, 3+comps*.5), "flera jämförbara aktiva priser")
    # 19 meaningful nominal margin
    margin=_n(asking.get("net_margin"))
    if margin>=50: add("nominal_margin", min(8, 3+margin/50), "meningsfull möjlig nettomarginal")
    # 20 reject obvious commodity/no-evidence crowding via negative signal
    if not sold and not comps and not identity.get("card_number") and not item.get("valuable_card_tags"):
        add("commodity_uncertainty", -8, "svagt kortspecifikt prisunderlag")
    # 31-50: additional discovery dimensions. These remain bounded clues,
    # never standalone valuation evidence.
    if item.get("parallel") or identity.get("parallel"): add("parallel_identity", 4, "parallel identifierad")
    if item.get("is_rookie") and identity.get("card_number"): add("rookie_exact", 3, "rookie med kortnummer")
    if item.get("case_hit") or item.get("ssp_evidence"): add("ssp_case_hit", 5, "SSP/case-hit-signal")
    if item.get("variation_evidence"): add("variation", 4, "variant/variation-signal")
    if item.get("short_print_evidence"): add("short_print", 4, "short-print-signal")
    if item.get("auction_ending_soon") and int(_n(item.get("bid_count")))==0: add("ending_unbid", 3, "snart slut utan bud")
    if item.get("buy_now") and total>0: add("buy_now_actionable", 2, "direkt köpbar")
    if item.get("seller_feedback_score") and _n(item.get("seller_feedback_score"))>=98: add("seller_quality", 1, "stark säljarhistorik")
    if item.get("image_count") and _n(item.get("image_count"))>=2: add("image_coverage", 1, "flera annonsbilder")
    if item.get("condition") and not item.get("condition_risk"): add("condition_stated", 1, "skick angivet")
    if item.get("market_edge_score") and _n(item.get("market_edge_score"))>=60: add("market_edge", 4, "marknadsedge")
    if item.get("visual_edge_score") and _n(item.get("visual_edge_score"))>=60: add("visual_edge", 3, "visuell edge")
    if item.get("collector_signal_score") and _n(item.get("collector_signal_score"))>=10: add("collector_signal", 3, "samlarvärdessignal")
    if item.get("rookie_importance_matched"): add("rookie_importance", 2, "relevant rookieprofil")
    if item.get("player_card_demand_review_priority_score") and _n(item.get("player_card_demand_review_priority_score"))>=12: add("review_priority", 2, "stark review-prioritet")
    if item.get("mispricing_supported"): add("supported_mispricing", 6, "prisgap stöds av data")
    if item.get("exact_supply_count") == 0 and (sold or comps): add("scarce_supply", 3, "låg observerad tillgång")
    if item.get("exact_supply_count") and _n(item.get("exact_supply_count"))>=10 and not sold: add("oversupply", -4, "hög tillgång utan säljbevis")
    if item.get("shipping_known") is True: add("shipping_known", 2, "frakt verifierad")
    if item.get("shipping_known") is False: add("shipping_unknown", -3, "frakt osäker")
    return signals


def opportunity_discovery_score(item):
    return round(sum(s["score"] for s in opportunity_discovery_signals(item)),2)
