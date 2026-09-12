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
    """Best-effort player key for Top-3 diversity only.

    This key never verifies identity and never affects valuation. It only stops
    several listings for the same obvious player from monopolising the novice
    Top-3 when comparable alternatives exist.
    """
    fields=item.get("exact_identity_gate_identity_fields") or {}
    if isinstance(fields,dict):
        player=fields.get("player_name")
        if player:
            return _norm_text(player)
    for key in ("player_name","player","spelare"):
        if item.get(key):
            return _norm_text(item.get(key))
    title=_norm_text(item.get("titel") or item.get("title"))
    # Reuse already-known player labels when present, but do not try to invent a
    # generic name parser here. Famous-player knowledge is enough for diversity.
    profile=item.get("player_profile") or {}
    if isinstance(profile,dict) and profile.get("name"):
        return _norm_text(profile.get("name"))
    matched=item.get("matched_player_name") or item.get("player_match_name")
    if matched:
        return _norm_text(matched)
    # Last resort: title itself keeps exact duplicate listings together without
    # claiming that we know the player's identity.
    return title


def _decision_certainty(item, sold_count, identity_ok):
    """Evidence-aware certainty for the novice Top-3.

    Raw ranking/deal confidence can legitimately include easy player-name
    recognition. For a buy-facing Top-3, that must not look like 88/100 certainty
    when the exact card is still unverified and there are zero sold comps.
    """
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
    # Existing deal score is used only as opportunity potential, never certainty.
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


def _base_row(item):
    decision=str(item.get("beslut") or item.get("decision") or item.get("recommendation") or "EJ BESLUT").upper()
    sold=int(_n(item.get("sold_comparable_count"),0))
    identity_ok=bool(
        item.get("exact_identity_gate_supports_exact_comp_search")
        or item.get("exact_identity_gate_status") in {"READY","EXACT","STRONG"}
    )
    certainty,raw_certainty,certainty_limits=_decision_certainty(item,sold,identity_ok)
    blockers=list(item.get("decision_diagnostics") or [])
    market_value=_market_value(item)
    total_cost=item.get("analysis_total_cost") if item.get("analysis_total_cost") is not None else item.get("total_cost")
    economic_edge_ok,economic_edge_blockers,max_total_price=_economic_edge(item,decision,sold,identity_ok,market_value,total_cost)
    return {
        "title":_title(item),
        "url":_url(item),
        "decision":decision,
        "potential":_potential(item),
        "certainty":certainty,
        "raw_certainty":raw_certainty,
        "certainty_limits":certainty_limits,
        "player_key":_player_key(item),
        "sold_comps":sold,
        "identity_ok":identity_ok,
        "market_value":market_value,
        "total_cost":total_cost,
        "max_total_price":max_total_price,
        "economic_edge_ok":economic_edge_ok,
        "economic_edge_blockers":economic_edge_blockers,
        "shipping":item.get("frakt"),
        "shipping_known":item.get("shipping_known"),
        "primary_blocker":blockers[0] if blockers else None,
        "collector_worth_score":_n(item.get("collector_worth_score")),
        "collector_worth_label":item.get("collector_worth_label"),
        "collector_worth_value_basis":list(item.get("collector_worth_value_basis") or []),
        "collector_worth_strengths":list(item.get("collector_worth_strengths") or []),
        "collector_worth_cautions":list(item.get("collector_worth_cautions") or []),
        "collector_worth_hobby_traps":list(item.get("collector_worth_hobby_traps") or []),
        "card_hierarchy_score":_n(item.get("card_hierarchy_score")),
        "card_hierarchy_tier_label":item.get("card_hierarchy_tier_label"),
        "card_hierarchy_role_label":item.get("card_hierarchy_role_label"),
        "card_hierarchy_reasons":list(item.get("card_hierarchy_reasons") or []),
        "card_hierarchy_hobby_traps":list(item.get("card_hierarchy_hobby_traps") or []),
        "player_card_hierarchy_score":_n(item.get("player_card_hierarchy_score")),
        "player_card_hierarchy_confidence_score":_n(item.get("player_card_hierarchy_confidence_score")),
        "player_card_hierarchy_label":item.get("player_card_hierarchy_label"),
        "player_card_hierarchy_reasons":list(item.get("player_card_hierarchy_reasons") or []),
        "player_card_hierarchy_cautions":list(item.get("player_card_hierarchy_cautions") or []),
        "player_card_hierarchy_hobby_traps":list(item.get("player_card_hierarchy_hobby_traps") or []),
        # Keep the full analyzed listing available for drill-down UI.  The
        # novice Top-3 row is intentionally compact, but the explanation
        # popover needs the original identity/checklist/visual evidence.
        "_source_item": item,
    }


def build_decision_tiers(candidates, total_limit=3, require_verified_economic_edge=False):
    all_rows=[_base_row(i) for i in (candidates or [])]
    for r in all_rows:
        is_buy=r["decision"].startswith("KÖP") or r["decision"].startswith("KOP")
        r["tier"]=("VERIFIED" if is_buy and r["certainty"]>=60 and r["sold_comps"]>=2 and r["identity_ok"] and r["market_value"] is not None else "PROMISING" if r["potential"]>=55 else "REMAINDER")
    rows=[r for r in all_rows if r["economic_edge_ok"]] if require_verified_economic_edge else list(all_rows)
    tier_order={"VERIFIED":2,"PROMISING":1,"REMAINDER":0}
    rows.sort(key=lambda r:(tier_order[r["tier"]],r["certainty"],r["potential"],r["sold_comps"]),reverse=True)
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
    rejected=[r for r in all_rows if not r["economic_edge_ok"]]
    blocker_counts={}
    for r in rejected:
        for reason in r.get("economic_edge_blockers") or []: blocker_counts[reason]=blocker_counts.get(reason,0)+1
    return {"rows":selected,"verified_count":sum(1 for r in all_rows if r["tier"]=="VERIFIED"),"promising_count":sum(1 for r in all_rows if r["tier"]=="PROMISING"),"creates_new_decision":False,
        "duplicate_player_count":max(0,len(selected)-len({r.get("player_key") for r in selected if r.get("player_key")})),"rejected_count":len(rejected),"rejection_reasons":blocker_counts,
        "note":"Topplistan kan köras med hård verifierad economic-edge gate; spelarstatus och samlarintresse får då bara rangordna redan verifierade fynd."}
