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


def _norm_text(value):
    return " ".join(str(value or "").casefold().strip().split())


def _player_key(item):
    """Best-effort player key for Top-3 diversity only."""
    fields=item.get("exact_identity_gate_identity_fields") or {}
    if isinstance(fields,dict):
        player=fields.get("player_name")
        if player:
            return _norm_text(player)
    for key in ("player_name","player","spelare"):
        if item.get(key):
            return _norm_text(item.get(key))
    title=_norm_text(item.get("titel") or item.get("title"))
    profile=item.get("player_profile") or {}
    if isinstance(profile,dict) and profile.get("name"):
        return _norm_text(profile.get("name"))
    matched=item.get("matched_player_name") or item.get("player_match_name")
    if matched:
        return _norm_text(matched)
    return title


def _decision_certainty(item, sold_count, identity_ok):
    raw=_certainty(item)
    capped=raw
    reasons=[]
    if not identity_ok:
        capped=min(capped,54.0)
        reasons.append("exakt kortidentitet är inte verifierad")
    if sold_count<=0:
        capped=min(capped,49.0)
        reasons.append("inga verifierade exact SOLD-comps")
    elif sold_count==1:
        capped=min(capped,59.0)
        reasons.append("bara en verifierad exact SOLD-comp")
    return capped,raw,reasons


def _certainty(item):
    for key in ("ranking_confidence_score","deal_confidence_score","confidence","valuation_confidence_score"):
        if item.get(key) is not None:
            return max(0.0,min(100.0,_n(item.get(key))))
    return 0.0


def _potential(item):
    return max(0.0,min(100.0,_n(item.get("deal_score"))))


def _market_value(item):
    if item.get("valuation_display_safe") is not True:
        return None
    for key in ("market_value_estimate","expected_resale","estimated_market_value","marknadsvarde"):
        if item.get(key) is not None:
            return _n(item.get(key))
    return None


def _economic_edge(item, decision, sold_count, identity_ok, market_value, total_cost):
    reasons=[]
    if not identity_ok: reasons.append("exakt identitet ej verifierad")
    if sold_count < 2: reasons.append("färre än 2 verifierade exact SOLD")
    if market_value is None or market_value <= 0: reasons.append("inget verifieringsbart marknadsvärde")
    if total_cost is None or _n(total_cost, -1) < 0: reasons.append("total köpkostnad saknas")
    max_total=item.get("dynamic_max_total_price")
    if max_total is None: max_total=item.get("max_total_price")
    max_total=_n(max_total, 0)
    if max_total <= 0: reasons.append("evidensbaserat maxpris saknas")
    elif total_cost is not None and _n(total_cost) > max_total: reasons.append("köpkostnaden överstiger evidensbaserat maxpris")
    if not (decision.startswith("KÖP") or decision.startswith("KOP")): reasons.append("analysen ger inte KÖP")
    return (not reasons), reasons, max_total


def _research_ready(item):
    return bool(
        item.get("exact_identity_gate_supports_comp_research")
        or item.get("exact_identity_gate_supports_exact_comp_search")
        or item.get("exact_identity_gate_status") in {"SÖKBAR_TITEL","SÖKBAR","VERIFIERAD","READY","EXACT","STRONG"}
    )


def _guide_context(item):
    """Read guide context already attached to an analysed candidate.

    Guide values are research-triage only. They never create market value, SOLD,
    max price or a BUY decision.
    """
    triage=item.get("guide_triage") or item.get("price_guide_triage") or {}
    if isinstance(triage,dict) and triage.get("status"):
        raw=triage.get("ungraded_usd")
        return {
            "status":str(triage.get("status")),
            "ungraded_usd":None if raw is None else _n(raw),
            "priority":int(_n(triage.get("priority"),1)),
        }
    scp=item.get("sports_cards_pro") or item.get("sportscardspro_context") or {}
    raw=None
    if isinstance(scp,dict) and scp.get("ok"):
        raw=scp.get("ungraded_usd")
    if raw is None:
        raw=item.get("price_guide_ungraded_usd")
    if raw is None:
        return {"status":"NO_GUIDE_CONTEXT","ungraded_usd":None,"priority":1}
    raw=_n(raw)
    if raw <= 3:
        return {"status":"LOW_GUIDE_CONTEXT","ungraded_usd":raw,"priority":3}
    if raw <= 10:
        return {"status":"MODEST_GUIDE_CONTEXT","ungraded_usd":raw,"priority":2}
    return {"status":"MEANINGFUL_GUIDE_CONTEXT","ungraded_usd":raw,"priority":0}


def _structural_merit(item):
    """Best-effort card-specific merit for fallback research ordering."""
    features=item.get("features") or item.get("card_features") or {}
    if not isinstance(features,dict):
        features={}
    merit=max(
        _n(item.get("collector_worth_score"),0),
        _n(item.get("card_hierarchy_score"),0),
        _n(item.get("player_card_hierarchy_score"),0),
        _n(item.get("nonstandard_value_driver_score"),0),
        _n(item.get("oddity_story_score"),0),
    )
    if any(features.get(k) for k in ("is_rookie","is_auto","is_patch","is_jersey","is_serial_numbered","is_case_hit","is_ssp","is_sp","is_1of1")):
        merit=max(merit,70)
    if item.get("is_hidden_find_candidate") or item.get("misclassified_card_candidate") or item.get("mispriced_rookie_candidate"):
        merit=max(merit,65)
    return min(100.0,merit)


def _investigate_score(item, potential, certainty, sold_count, research_ready, identity_ok):
    """Rank research candidates by expected next-step usefulness, not hype alone.

    This score is never a valuation and never creates BUY. It only decides which
    unverified listings deserve attention first when the strict BUY gate is empty.
    """
    score = potential * 0.48 + certainty * 0.12
    reasons=[]
    if research_ready:
        score += 18
        reasons.append("sökbar comp-identitet")
    if identity_ok:
        score += 8
        reasons.append("beslutsstark identitet")
    if sold_count == 1:
        score += 10
        reasons.append("bara en exact SOLD saknas till två-comp-tröskeln")
    elif sold_count >= 2:
        score += 12
        reasons.append("exact SOLD finns redan")
    if item.get("is_information_edge_candidate") or item.get("is_market_edge_candidate"):
        score += 7
        reasons.append("informations-/marknadssignal")
    if item.get("is_hidden_find_candidate") or item.get("misclassified_card_candidate") or item.get("mispriced_rookie_candidate"):
        score += 6
        reasons.append("discovery-signal")
    oddity = _n(item.get("oddity_story_score") or item.get("nonstandard_value_driver_score"), 0)
    if oddity > 0:
        score += min(6, oddity * 0.06)
        reasons.append("ovanlig värdedrivare värd kontroll")
    collector = _n(item.get("collector_worth_score"), 0)
    hierarchy = _n(item.get("card_hierarchy_score"), 0)
    score += min(5, collector * 0.03)
    score += min(5, hierarchy * 0.03)

    guide=_guide_context(item)
    merit=_structural_merit(item)
    if guide["status"]=="LOW_GUIDE_CONTEXT" and sold_count < 2:
        score -= 28
        reasons.append(f"låg prisguidekontext ~${guide['ungraded_usd']:.2f} raw")
    elif guide["status"]=="MODEST_GUIDE_CONTEXT" and sold_count < 2:
        score -= 8
    if identity_ok and sold_count == 0 and merit < 35:
        score -= 14
        reasons.append("exact ID men svag kortspecifik merit")
    return round(max(0.0,min(100.0, score)), 1), reasons[:5]


def _base_row(item):
    decision=str(item.get("beslut") or item.get("decision") or item.get("recommendation") or "EJ BESLUT").upper()
    sold=int(_n(item.get("sold_comparable_count"),0))
    identity_ok=bool(item.get("exact_identity_gate_supports_exact_comp_search") or item.get("exact_identity_gate_status") in {"READY","EXACT","STRONG"})
    research_ready=_research_ready(item)
    certainty,raw_certainty,certainty_limits=_decision_certainty(item,sold,identity_ok)
    blockers=list(item.get("decision_diagnostics") or [])
    market_value=_market_value(item)
    total_cost=item.get("analysis_total_cost") if item.get("analysis_total_cost") is not None else item.get("total_cost")
    economic_edge_ok,economic_edge_blockers,max_total_price=_economic_edge(item,decision,sold,identity_ok,market_value,total_cost)
    potential=_potential(item)
    investigate_score, investigate_reasons = _investigate_score(item,potential,certainty,sold,research_ready,identity_ok)
    guide=_guide_context(item)
    merit=_structural_merit(item)
    return {
        "title":_title(item),"url":_url(item),"decision":decision,"original_decision":decision,
        "potential":potential,"certainty":certainty,"raw_certainty":raw_certainty,"certainty_limits":certainty_limits,
        "player_key":_player_key(item),"sold_comps":sold,"identity_ok":identity_ok,"research_ready":research_ready,
        "investigate_score":investigate_score,"investigate_reasons":investigate_reasons,
        "guide_status":guide["status"],"guide_ungraded_usd":guide["ungraded_usd"],"guide_priority":guide["priority"],
        "structural_merit":merit,
        "market_value":market_value,"total_cost":total_cost,"max_total_price":max_total_price,"economic_edge_ok":economic_edge_ok,
        "economic_edge_blockers":economic_edge_blockers,"shipping":item.get("frakt"),"shipping_known":item.get("shipping_known"),
        "primary_blocker":blockers[0] if blockers else None,
        "collector_worth_score":_n(item.get("collector_worth_score")),"collector_worth_label":item.get("collector_worth_label"),
        "collector_worth_value_basis":list(item.get("collector_worth_value_basis") or []),"collector_worth_strengths":list(item.get("collector_worth_strengths") or []),
        "collector_worth_cautions":list(item.get("collector_worth_cautions") or []),"collector_worth_hobby_traps":list(item.get("collector_worth_hobby_traps") or []),
        "card_hierarchy_score":_n(item.get("card_hierarchy_score")),"card_hierarchy_tier_label":item.get("card_hierarchy_tier_label"),
        "card_hierarchy_role_label":item.get("card_hierarchy_role_label"),"card_hierarchy_reasons":list(item.get("card_hierarchy_reasons") or []),
        "card_hierarchy_hobby_traps":list(item.get("card_hierarchy_hobby_traps") or []),"player_card_hierarchy_score":_n(item.get("player_card_hierarchy_score")),
        "player_card_hierarchy_confidence_score":_n(item.get("player_card_hierarchy_confidence_score")),"player_card_hierarchy_label":item.get("player_card_hierarchy_label"),
        "player_card_hierarchy_reasons":list(item.get("player_card_hierarchy_reasons") or []),"player_card_hierarchy_cautions":list(item.get("player_card_hierarchy_cautions") or []),
        "player_card_hierarchy_hobby_traps":list(item.get("player_card_hierarchy_hobby_traps") or []),"_source_item":item,
    }


def _select_diverse(rows,total_limit):
    selected=[]; used_players=set()
    for tier in ("VERIFIED","PROMISING","REMAINDER"):
        for row in rows:
            if len(selected)>=total_limit: break
            if row["tier"]!=tier or row in selected: continue
            player=row.get("player_key") or ""
            if player and player in used_players: continue
            selected.append(row)
            if player: used_players.add(player)
            break
    for row in rows:
        if len(selected)>=total_limit: break
        player=row.get("player_key") or ""
        if row not in selected and (not player or player not in used_players):
            selected.append(row)
            if player: used_players.add(player)
    for row in rows:
        if len(selected)>=total_limit: break
        if row not in selected: selected.append(row)
    return selected


def _is_low_value_noise(row):
    """Return True for guide-confirmed cheap cards with weak card-specific merit.

    This is presentation triage only. A row is suppressible only when it has no
    exact SOLD evidence and there are enough better candidates to fill Top 5.
    """
    if row.get("guide_status") != "LOW_GUIDE_CONTEXT":
        return False
    if int(row.get("sold_comps") or 0) > 0:
        return False
    if _n(row.get("structural_merit"),0) >= 55:
        return False
    source=row.get("_source_item") or {}
    if source.get("is_information_edge_candidate") or source.get("is_market_edge_candidate"):
        return False
    if source.get("is_hidden_find_candidate") or source.get("misclassified_card_candidate") or source.get("mispriced_rookie_candidate"):
        return False
    return True


def build_decision_tiers(candidates, total_limit=5, require_verified_economic_edge=False):
    all_rows=[_base_row(i) for i in (candidates or [])]
    for r in all_rows:
        is_buy=r["decision"].startswith("KÖP") or r["decision"].startswith("KOP")
        r["tier"]=("VERIFIED" if is_buy and r["certainty"]>=60 and r["sold_comps"]>=2 and r["identity_ok"] and r["market_value"] is not None else "PROMISING" if r["potential"]>=55 else "REMAINDER")

    fallback_investigate_mode=False
    suppressed_low_value=[]
    if require_verified_economic_edge:
        rows=[r for r in all_rows if r["economic_edge_ok"]]
        if not rows:
            rows=list(all_rows)
            fallback_investigate_mode=bool(rows)
            for r in rows:
                r["tier"]="PROMISING"
                r["decision"]="UNDERSÖK"
                r["certainty_limits"]=list(dict.fromkeys((r.get("certainty_limits") or [])+(r.get("economic_edge_blockers") or [])))
            better=[r for r in rows if not _is_low_value_noise(r)]
            low_value=[r for r in rows if _is_low_value_noise(r)]
            if len(better) >= max(1,int(total_limit or 0)):
                rows=better
                suppressed_low_value=low_value
    else:
        rows=list(all_rows)

    tier_order={"VERIFIED":2,"PROMISING":1,"REMAINDER":0}
    if fallback_investigate_mode:
        # Research ordering must still care about economics. A famous player or
        # collectible-looking card must not outrank a cheaper listing merely
        # because its identity is easier to research.
        def _research_sort(r):
            cost=_n(r.get("total_cost"),999999)
            guide=_n(r.get("guide_ungraded_usd"),0)
            source=r.get("_source_item") or {}
            ask_to_guide=(cost/(guide*9.5)) if guide>0 and cost>=0 else 999
            obvious_overprice_penalty=35 if ask_to_guide>2.0 else (18 if ask_to_guide>1.25 else 0)
            economic_signal=max(0.0,100.0-obvious_overprice_penalty-min(35.0,max(0.0,ask_to_guide-0.65)*25.0))
            return (economic_signal,r["investigate_score"],r["structural_merit"],r["potential"],r["certainty"],-cost)
        rows.sort(key=_research_sort,reverse=True)
    else:
        rows.sort(key=lambda r:(tier_order[r["tier"]],r["potential"],r["certainty"],r["sold_comps"]),reverse=True)
    selected=_select_diverse(rows,total_limit)
    # Outside the strict economic-edge mode, older views may still ask for a
    # relative Top N of an already filtered pool. In strict mode, never fill
    # with weak ordinary rows just to reach five cards.
    target=min(max(0,int(total_limit or 0)),len(all_rows))
    if not require_verified_economic_edge and len(selected) < target:
        for r in all_rows:
            if len(selected) >= target:
                break
            if r in selected:
                continue
            r["tier"]="REMAINDER"
            if not r["economic_edge_ok"]:
                r["decision"]="UNDERSÖK"
            selected.append(r)
    rejected=[r for r in all_rows if not r["economic_edge_ok"]]
    blocker_counts={}
    for r in rejected:
        for reason in r.get("economic_edge_blockers") or []: blocker_counts[reason]=blocker_counts.get(reason,0)+1
    return {"rows":selected,"verified_count":sum(1 for r in all_rows if r["tier"]=="VERIFIED"),"promising_count":sum(1 for r in all_rows if r["tier"]=="PROMISING"),"creates_new_decision":False,
        "fallback_investigate_mode":fallback_investigate_mode,"duplicate_player_count":max(0,len(selected)-len({r.get("player_key") for r in selected if r.get("player_key")})),
        "suppressed_low_value_count":len(suppressed_low_value),
        "suppressed_low_value_titles":[r.get("title") for r in suppressed_low_value[:10]],
        "rejected_count":len(rejected),"rejection_reasons":blocker_counts,
        "note":"Verifierade KÖP visas först. Om inget klarar den hårda economic-edge-gaten visas i stället tydligt märkta UNDERSÖK-kandidater. Guidebekräftade lågpriskort med svag kortspecifik merit döljs från Top 5 när det finns tillräckligt många bättre alternativ. Guidevärden skapar aldrig marknadsvärde, SOLD-evidens, maxpris eller KÖP."}
