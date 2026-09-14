"""Prioritise candidates that are closest to crossing FlipFynd's evidence gate.

This queue never creates a valuation or BUY signal. It only estimates research
leverage from already-structured evidence. Exact identity is useful, but it must
not dominate the queue by itself: a cheap/common star-player insert should not
outrank a structurally stronger card merely because its identity is easier to
parse.
"""
from __future__ import annotations


def _n(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _txt(value):
    return " ".join(str(value or "").strip().split())


def _identity_ready(item):
    return bool(
        item.get("exact_identity_gate_supports_exact_comp_search")
        or item.get("exact_identity_gate_status") in {"READY", "EXACT", "STRONG", "VERIFIERAD", "SÖKBAR"}
    )


def _research_identity_ready(item):
    return bool(
        item.get("exact_identity_gate_supports_comp_research")
        or _identity_ready(item)
        or item.get("exact_identity_gate_status") == "SÖKBAR_TITEL"
    )


def _market_value_ready(item):
    return bool(
        item.get("valuation_display_safe") is True
        and any(item.get(k) is not None for k in (
            "market_value_estimate", "expected_resale", "estimated_market_value", "marknadsvarde"
        ))
    )


def _max_price_ready(item):
    return _n(item.get("dynamic_max_total_price") or item.get("max_total_price"), 0) > 0


def _player_key(item):
    gate = item.get("exact_identity_gate_research_identity_fields") or item.get("exact_identity_gate_identity_fields") or {}
    if isinstance(gate, dict) and gate.get("player_name"):
        return _txt(gate.get("player_name")).casefold()
    for key in ("player_name", "matched_player_name", "player_match_name", "spelare"):
        if item.get(key):
            return _txt(item.get(key)).casefold()
    return ""


def _guide_context(item):
    triage = item.get("guide_triage") or item.get("price_guide_triage") or {}
    if isinstance(triage, dict) and triage.get("status"):
        return {
            "status": str(triage.get("status")),
            "ungraded_usd": None if triage.get("ungraded_usd") is None else _n(triage.get("ungraded_usd")),
            "priority": int(_n(triage.get("priority"), 1)),
        }
    scp = item.get("sports_cards_pro") or item.get("sportscardspro_context") or {}
    if isinstance(scp, dict) and scp.get("ok"):
        raw = scp.get("ungraded_usd")
        if raw is not None:
            raw = _n(raw)
            if raw <= 3:
                return {"status": "LOW_GUIDE_CONTEXT", "ungraded_usd": raw, "priority": 3}
            if raw <= 10:
                return {"status": "MODEST_GUIDE_CONTEXT", "ungraded_usd": raw, "priority": 2}
            return {"status": "MEANINGFUL_GUIDE_CONTEXT", "ungraded_usd": raw, "priority": 0}
    return {"status": "NO_GUIDE_CONTEXT", "ungraded_usd": None, "priority": 1}


def _structural_merit(item):
    score = 0.0
    reasons = []
    serial = _n(item.get("serial_number") or item.get("serial_denominator"), 0)
    if item.get("is_1of1"):
        score += 32; reasons.append("1/1")
    elif serial:
        score += 24 if serial <= 25 else 18 if serial <= 99 else 11 if serial <= 199 else 5
        reasons.append("numrerat")
    if item.get("is_auto") or item.get("autograph"):
        score += 22; reasons.append("autograf")
    if item.get("is_patch") or item.get("is_jersey") or item.get("is_game_worn"):
        score += 14; reasons.append("patch/relic")
    if item.get("is_rookie") and (item.get("rookie_importance_matched") or _n(item.get("rookie_importance_score"), 0) >= 60 or str(item.get("rookie_tier") or "").casefold() in {"iconic", "strong"}):
        score += 15; reasons.append("relevant rookie")
    score += min(16, _n(item.get("valuable_structure_score"), 0) * 0.16)
    score += min(14, _n(item.get("card_hierarchy_score") or item.get("hierarchy_score"), 0) * 0.14)
    score += min(10, max(0, _n(item.get("collector_worth_score"), 0) - 45) * 0.20)
    if item.get("is_case_hit") or item.get("case_hit"):
        score += 18; reasons.append("case hit")
    if item.get("is_short_print") or item.get("is_ssp") or item.get("short_print"):
        score += 16; reasons.append("SP/SSP")
    if item.get("is_hidden_find_candidate") or item.get("misclassified_card_candidate") or item.get("mispriced_rookie_candidate"):
        score += 10; reasons.append("discovery-signal")
    if item.get("is_market_edge_candidate") or item.get("is_information_edge_candidate"):
        score += 8; reasons.append("informationsövertag")
    if item.get("oddity_story_candidate") or item.get("visual_oddity_candidate"):
        score += 10; reasons.append("oddity/story")
    if item.get("parallel") or item.get("is_parallel"):
        score += 4; reasons.append("parallel")
    verdict = str(item.get("collector_worth_verdict") or item.get("collector_profile_verdict") or "").upper()
    traps = " ".join(str(x) for x in (item.get("collector_worth_hobby_traps") or item.get("hobby_traps") or []))
    if verdict == "SPELARDRIVET_STANDARDKORT" or "standardkort" in traps.casefold():
        score -= 22; reasons.append("stjärnspelare men standardkort")
    return max(0.0, min(100.0, score)), list(dict.fromkeys(reasons))[:6]


def _unlock_score(item):
    sold = int(_n(item.get("sold_comparable_count"), 0)); identity = _identity_ready(item); research_identity = _research_identity_ready(item)
    market = _market_value_ready(item); max_price = _max_price_ready(item); merit, _ = _structural_merit(item); guide = _guide_context(item)
    if identity and sold == 1: score = 100.0
    elif identity and sold == 0: score = 70.0
    elif research_identity and sold == 0: score = 66.0
    elif sold >= 2 and not (market and max_price): score = 74.0
    elif not identity: score = 38.0
    else: score = 52.0
    score += min(18.0, merit * 0.30)
    if guide["status"] == "LOW_GUIDE_CONTEXT" and sold < 2: score -= 34.0
    elif guide["status"] == "MODEST_GUIDE_CONTEXT" and sold < 2: score -= 10.0
    if market: score += 4
    if max_price: score += 4
    score += min(4.0, max(0.0, _n(item.get("deal_score"))) * 0.04)
    return score


def _status(item):
    sold = int(_n(item.get("sold_comparable_count"), 0)); identity = _identity_ready(item); research_identity = _research_identity_ready(item)
    market = _market_value_ready(item); max_price = _max_price_ready(item); merit, _ = _structural_merit(item); guide = _guide_context(item)
    if identity and sold == 1: return "ONE_SALE_AWAY", "1 extra verifierad exact SOLD kan räcka för att nå comp-tröskeln."
    if identity and sold == 0 and guide["status"] == "LOW_GUIDE_CONTEXT":
        raw = guide.get("ungraded_usd"); suffix = f" (~${raw:.2f} raw)" if raw is not None else ""
        return "EXACT_READY_LOW_GUIDE", f"Exakt identitet finns, men prisguidekontexten är låg{suffix}. Researcha starkare kandidater först."
    if identity and sold == 0 and merit < 40: return "EXACT_READY_LOW_MERIT", "Exakt identitet finns, men kortet saknar hittills starka kortspecifika värdedrivare. Researcha först starkare kandidater."
    if identity and sold == 0: return "EXACT_READY_NO_SALES", "Exakt identitet är redo; nästa steg är att hitta första verifierade exact SOLD."
    if research_identity and sold == 0: return "RESEARCH_READY_NO_SALES", "Titeln är strukturerad nog för smal comp-research; verifiera identiteten innan en sale får räknas som exact."
    if sold >= 2 and not market: return "VALUATION_NEXT", "SOLD-underlag finns, men säker värdering är ännu inte upplåst."
    if sold >= 2 and market and not max_price: return "MAX_PRICE_NEXT", "Värdering finns; nästa steg är evidensbaserat maxpris."
    if not identity: return "IDENTITY_FIRST", "Verifiera exakt kortidentitet innan comp-research."
    return "REVIEW", "Granska nästa saknade evidenssteg."


def _is_actionable_research_row(row, min_merit=18):
    """Return whether a row deserves scarce comp-research time."""
    if row.get("status") in {"ONE_SALE_AWAY", "VALUATION_NEXT", "MAX_PRICE_NEXT"}:
        return True
    if row.get("status") in {"EXACT_READY_NO_SALES", "RESEARCH_READY_NO_SALES"}:
        return _n(row.get("research_merit_score"), 0) >= max(0, _n(min_merit, 18))
    return False


def build_unlock_research_queue(items, limit=10, *, actionable_only=False, min_merit=18):
    rows = []
    for item in items or []:
        if not isinstance(item, dict): continue
        title = _txt(item.get("titel") or item.get("title"))
        if not title: continue
        sold = int(_n(item.get("sold_comparable_count"), 0)); status, action = _status(item); merit, merit_reasons = _structural_merit(item); guide = _guide_context(item); unlock = _unlock_score(item)
        rows.append({
            "title": title, "url": item.get("lank") or item.get("url"), "player_key": _player_key(item), "status": status, "action": action,
            "unlock_score": unlock, "research_value_score": unlock, "research_merit_score": round(merit), "research_merit_reasons": merit_reasons,
            "guide_status": guide["status"], "guide_ungraded_usd": guide["ungraded_usd"], "sold_comps": sold,
            "identity_ready": _identity_ready(item), "research_identity_ready": _research_identity_ready(item), "market_value_ready": _market_value_ready(item),
            "max_price_ready": _max_price_ready(item), "potential": max(0.0, min(100.0, _n(item.get("deal_score")))), "source_item": item,
        })
    counts={}
    for row in rows: counts[row["status"]]=counts.get(row["status"],0)+1
    suppressed_count = 0
    if actionable_only:
        kept = [row for row in rows if _is_actionable_research_row(row, min_merit=min_merit)]
        suppressed_count = len(rows) - len(kept)
        rows = kept
    status_order = {"ONE_SALE_AWAY":0,"VALUATION_NEXT":1,"MAX_PRICE_NEXT":2,"EXACT_READY_NO_SALES":3,"RESEARCH_READY_NO_SALES":4,"EXACT_READY_LOW_MERIT":5,"EXACT_READY_LOW_GUIDE":6,"IDENTITY_FIRST":7,"REVIEW":8}
    rows.sort(key=lambda r:(status_order.get(r["status"],9),-r["unlock_score"],-r["research_merit_score"],-r["potential"],r["title"]))
    selected, used_players = [], set()
    for row in rows:
        pk=row.get("player_key")
        if pk and pk in used_players: continue
        selected.append(row)
        if pk: used_players.add(pk)
        if len(selected)>=max(0,int(limit)): break
    for row in rows:
        if len(selected)>=max(0,int(limit)): break
        if row not in selected: selected.append(row)
    return {"rows":selected,"counts":counts,"total":sum(counts.values()),"actionable_total":len(rows),"suppressed_count":suppressed_count,"near_unlock_count":counts.get("ONE_SALE_AWAY",0),"exact_ready_no_sales_count":counts.get("EXACT_READY_NO_SALES",0),"low_merit_exact_count":counts.get("EXACT_READY_LOW_MERIT",0),"low_guide_exact_count":counts.get("EXACT_READY_LOW_GUIDE",0),"note":"Researchkön visar bara evidensnära kort eller noll-sale-kort med tydlig kortspecifik samlarmerit. Svaga bas- och standardkort används inte som utfyllnad. Exact ID eller en sökbar titel räcker aldrig ensamt och guidevärden skapar aldrig KÖP."}
