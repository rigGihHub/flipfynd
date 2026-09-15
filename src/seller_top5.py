"""Rank the best current FlipFynd card candidates from one Tradera seller.

Seller-specific logic is deliberately limited to inventory filtering and cheap
triage. Final decisions and final ordering reuse the normal FlipFynd full
analysis contract: rank_score, player_market_score, risk_adjusted_profit.

Seller Top 5 is sport-agnostic at product level: supported hockey and football
cards compete in one final ranking. The UI does not need to choose a sport.
"""
from __future__ import annotations

from typing import Callable, Iterable

from src.seller_card_domain import seller_item_domain_check
from src.seller_live_quick_analysis import quick_analyze_seller_inventory
from src.seller_live_full_analysis import full_analyze_live_seller_item
from src.card_parser import parse_card_features
from src.adaptive_deepening import select_dynamic_seller_deep_rows
from src.seller_card_merit import assess_seller_card_merit
from src.fast_analysis_pool import select_fast_analysis_pool
from src.analysis_budget import fast_analysis_budget
from src.deal_readiness import assess_deal_readiness


def _emit(callback, **payload):
    if not callable(callback):
        return
    try:
        callback(dict(payload))
    except Exception:
        pass


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _identity_key(item: dict) -> str:
    for key in ("tradera_item_id", "id", "item_id", "lank", "url", "link"):
        value = item.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return str(item.get("titel") or item.get("title") or "").strip().casefold()


def _card_opportunity_key(row: dict) -> str:
    """Collapse separate listings of the same identifiable card in Top 5."""
    source = row.get("source_item") or row
    title = str(source.get("titel") or source.get("title") or row.get("title") or "").strip()
    features = parse_card_features(title)
    identity = tuple(
        str(features.get(key) or "").strip().casefold()
        for key in ("season", "set_name", "card_number", "player_name", "parallel", "grading_company", "grade")
    )
    if identity[0] and identity[1] and identity[2] and identity[3]:
        return "card:" + "|".join(identity)
    return "listing:" + _identity_key(source)


def _explicit_condition_risk(row: dict) -> bool:
    source = row.get("source_item") or row
    text = " ".join(
        str(source.get(key) or row.get(key) or "")
        for key in ("titel", "title", "description", "full_description")
    ).casefold()
    return any(token in text for token in (
        "märken på", "skadad", "skador", "dåligt skick", "poor condition",
        "crease", "creased", "veck", "repor", "repa", "corner damage",
        "kantstött", "kantstötning",
    ))


def _select_diverse_rows(rows: list[dict], limit: int = 5) -> tuple[list[dict], int, int]:
    clean, condition_risk = [], []
    seen = set()
    duplicate_count = 0
    for row in rows:
        key = _card_opportunity_key(row)
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        (condition_risk if _explicit_condition_risk(row) else clean).append(row)
    selected = clean[:limit]
    if len(selected) < limit:
        for raw in condition_risk[: limit - len(selected)]:
            row = dict(raw)
            row["condition_risk"] = True
            row["label"] = "SKICKRISK · BÄST AV RESTEN"
            selected.append(row)
    return selected, duplicate_count, len(condition_risk)


def _supported_sport(item: dict, fallback: str = "hockey") -> str:
    text = " ".join(
        str(item.get(key) or "")
        for key in (
            "titel", "title", "source_category", "category_name", "category",
            "breadcrumb", "path", "raw_text", "full_description", "description",
        )
    ).casefold()
    football_tokens = (
        "fotboll", "football", "soccer", "premier league", "champions league",
        "uefa", "fifa", "match attax", "adrenalyn", "la liga", "serie a",
        "bundesliga", "world cup",
    )
    hockey_tokens = (
        "hockey", "nhl", "upper deck", "o-pee-chee", "opc", "young guns",
        "ice hockey", "shl",
    )
    football_hits = sum(token in text for token in football_tokens)
    hockey_hits = sum(token in text for token in hockey_tokens)
    if football_hits > hockey_hits:
        return "football"
    if hockey_hits > football_hits:
        return "hockey"
    if fallback in {"hockey", "football"}:
        return fallback
    return "hockey"


def _ordinary_rank_key(row: dict):
    return (
        _num(row.get("rank_score")),
        _num(row.get("player_market_score")),
        _num(row.get("risk_adjusted_profit")),
    )


def _seller_opportunity_rank_key(row: dict):
    """Order seller candidates without weakening ordinary BUY evidence gates."""
    decision = str(row.get("decision") or "").upper()
    decision_tier = 2 if decision.startswith("KÖP") else 1 if decision.startswith("UNDERSÖK") else 0
    sold = int(_num(row.get("sold_comps")))
    evidence_tier = 1 if row.get("identity_ok") and sold > 0 else 0
    collector = min(40.0, _num(row.get("collector_signal_score")))
    merit = assess_seller_card_merit(row)
    deal = _num(row.get("deal_score"))
    profit = _num(row.get("risk_adjusted_profit"))
    economic_tier = 2 if deal >= 30 and profit > 0 else 1 if deal > 0 and profit >= 0 else 0
    opportunity_score = _seller_opportunity_score(row)
    return (
        decision_tier,
        evidence_tier,
        economic_tier,
        opportunity_score,
        deal,
        profit,
        merit["score"],
        _num(row.get("rank_score")),
        _num(row.get("player_market_score")),
    )


def _seller_opportunity_score(row: dict) -> float:
    collector = min(40.0, _num(row.get("collector_signal_score")))
    merit = assess_seller_card_merit(row)
    deal = _num(row.get("deal_score"))
    profit = _num(row.get("risk_adjusted_profit"))
    sold = int(_num(row.get("sold_comps")))
    score = deal * 0.55 + _num(row.get("rank_score")) * 0.25 + merit["score"] * 0.15 + collector * 0.05
    # Scarcity can route a card into research, but cannot manufacture economic
    # promise when full analysis found no SOLD evidence and negative margin.
    if deal <= 10 and profit <= 0 and sold == 0:
        score = min(score, 25.0)
    return round(max(0.0, min(100.0, score)), 1)


def _quick_rank_key(row: dict):
    decision = str(row.get("decision") or "").upper()
    sold = int(_num(row.get("sold_comps")))
    identity_ok = bool(row.get("identity_ok"))
    decision_tier = 0 if decision.startswith("KÖP") else 1 if decision.startswith("UNDERSÖK") else 2
    evidence_tier = 0 if identity_ok and sold > 0 else 1
    collector = min(40.0, _num(row.get("collector_signal_score")))
    opportunity_score = _num(row.get("rank_score")) + collector * 1.5
    return (
        decision_tier,
        evidence_tier,
        -opportunity_score,
        -_num(row.get("rank_score")),
        -_num(row.get("player_market_score")),
        -_num(row.get("risk_adjusted_profit")),
        -sold,
        -_num(row.get("quick_score")),
        -_num(row.get("collector_signal_score")),
        _num(row.get("price"), 10**12),
    )


def _seller_presentation_label(row: dict) -> dict:
    out = dict(row)
    decision = str(out.get("decision") or "SKIP").upper()
    if decision.startswith("KÖP"):
        out["label"] = "KÖP-KANDIDAT"
    elif decision.startswith("UNDERSÖK"):
        out["label"] = "VÄRT ATT UNDERSÖKA"
    else:
        out["label"] = "BÄST AV RESTEN"
    return out


def seller_result_tier(row: dict) -> str:
    """Separate actual finds from research candidates and weak filler."""
    decision = str(row.get("decision") or "SKIP").upper()
    readiness = assess_deal_readiness(row)
    if decision.startswith("KÖP") and readiness["ready_for_find"]:
        return "FIND"
    if decision.startswith("KÖP"):
        return "RESEARCH"
    merit = assess_seller_card_merit(row)
    if merit["eligible"] and (
        decision.startswith("UNDERSÖK")
        or merit["score"] >= 25
        or (merit["strong_signals"] and merit["score"] >= 18)
    ):
        return "RESEARCH"
    return "WEAK"


def _quick_scan_inventory(alias: str, inventory: list[dict], *, analyze_fn: Callable, sport: str, quick_limit: int, progress_callback=None) -> dict:
    anchor = {"saljare": alias, "tradera_item_id": "__seller_top5_anchor__"}
    batch_size = max(20, min(int(quick_limit or 60), 100))
    unique: dict[str, dict] = {}
    for row in inventory:
        key = _identity_key(row)
        if key:
            unique[key] = row
    unique_inventory = list(unique.values())
    fast_pool = select_fast_analysis_pool(
        unique_inventory,
        cap=fast_analysis_budget(len(unique_inventory), context="seller"),
        exploration_fraction=0.30,
    )
    groups = {"hockey": [], "football": []}
    for row in fast_pool:
        groups[_supported_sport(row, fallback=sport)].append(row)

    all_rows: dict[str, dict] = {}
    failed = 0
    batches = 0
    domain_rejected = 0
    analysed_so_far = 0
    total = len(fast_pool)
    _emit(progress_callback, phase="quick_start", done=0, total=total, percent=28)

    for group_sport in ("hockey", "football"):
        group = groups[group_sport]
        for start in range(0, len(group), batch_size):
            batch = group[start:start + batch_size]
            if not batch:
                continue
            batches += 1
            quick = quick_analyze_seller_inventory(
                anchor, batch, analyze_fn=analyze_fn, sport=group_sport,
                strategy_mode="quick_flip", limit=len(batch), shortlist=min(5, len(batch)),
            )
            failed += int(quick.get("failed_count") or 0)
            domain_rejected += int(quick.get("domain_rejected_count") or 0)
            analysed_so_far += len(batch)
            for row in quick.get("rows") or []:
                source = row.get("source_item") or {}
                row = dict(row)
                row["sport"] = group_sport
                key = _identity_key(source) or _identity_key(row)
                if not key:
                    continue
                previous = all_rows.get(key)
                if previous is None or _quick_rank_key(row) < _quick_rank_key(previous):
                    all_rows[key] = row
            pct = 28 + int(37 * min(1.0, analysed_so_far / max(1, total)))
            _emit(progress_callback, phase="quick_progress", done=min(analysed_so_far, total), total=total, percent=pct, sport=group_sport)

    rows = list(all_rows.values())
    rows.sort(key=_quick_rank_key)
    _emit(progress_callback, phase="quick_complete", done=total, total=total, percent=65)
    return {
        "rows": rows,
        "analysed_count": len(rows),
        "failed_count": failed,
        "batch_count": batches,
        "domain_rejected_count": domain_rejected,
        "inventory_unique_count": len(unique_inventory),
        "cheap_coverage_complete": True,
        "fast_pool_count": len(fast_pool),
        "coverage_complete": len(rows) + failed + domain_rejected >= len(fast_pool),
        "sport_counts": {key: len(value) for key, value in groups.items()},
    }


def _fallback_row(qrow: dict, alias: str) -> dict:
    decision = str(qrow.get("decision") or "SKIP")
    decision_upper = decision.upper()
    if decision_upper.startswith("KÖP"):
        label = "KÖP-KANDIDAT · SNABBANALYS"
    elif decision_upper.startswith("UNDERSÖK"):
        label = "VÄRT ATT UNDERSÖKA · SNABBANALYS"
    else:
        label = "BÄST AV RESTEN · SNABBANALYS"
    return {
        "title": qrow.get("title"), "price": qrow.get("price"), "url": qrow.get("url"),
        "decision": decision, "label": label,
        "reason": "Reservresultat från snabbanalysen eftersom färre än fem fullanalyser lyckades.",
        "identity_ok": qrow.get("identity_ok"), "sold_comps": qrow.get("sold_comps", 0),
        "valuation_confidence": qrow.get("valuation_confidence", 0),
        "market_edge": qrow.get("market_edge", 0), "quick_score": qrow.get("quick_score", 0),
        "deal_score": qrow.get("deal_score", 0),
        "rank_score": qrow.get("rank_score", 0),
        "player_market_score": qrow.get("player_market_score", 0),
        "risk_adjusted_profit": qrow.get("risk_adjusted_profit", 0),
        "sport": qrow.get("sport"),
        "seller": alias, "source_item": qrow.get("source_item") or {},
        "analysis_level": "quick_fallback",
    }


def build_seller_top5(seller_alias: str, items: Iterable[dict] | None, *, analyze_fn: Callable,
                      sport: str = "all", quick_limit: int = 60, full_limit: int = 10,
                      progress_callback=None) -> dict:
    alias = str(seller_alias or "").strip()
    raw_inventory = [dict(x) for x in (items or []) if isinstance(x, dict)]
    if not alias:
        return {"status": "NO_SELLER", "rows": [], "seller": None, "inventory_count": len(raw_inventory)}
    if not raw_inventory:
        return {"status": "NO_ITEMS", "rows": [], "seller": alias, "inventory_count": 0}

    _emit(progress_callback, phase="filter_start", done=0, total=len(raw_inventory), percent=20)
    rejected = []
    inventory = []
    for idx, item in enumerate(raw_inventory, start=1):
        check = seller_item_domain_check(item, sport="all")
        if check.get("allowed"):
            inventory.append(item)
        else:
            rejected.append({"title": check.get("title"), "reason": check.get("reason")})
        if idx == len(raw_inventory) or idx % 100 == 0:
            _emit(progress_callback, phase="filter_progress", done=idx, total=len(raw_inventory), percent=20 + int(8 * idx / max(1, len(raw_inventory))))

    if not inventory:
        _emit(progress_callback, phase="complete", done=0, total=0, percent=100)
        return {"status": "NO_CARD_ITEMS", "rows": [], "seller": alias,
                "inventory_count": len(raw_inventory), "card_inventory_count": 0,
                "domain_rejected_count": len(rejected)}

    fallback_sport = sport if sport in {"hockey", "football"} else "hockey"
    quick = _quick_scan_inventory(
        alias, inventory, analyze_fn=analyze_fn, sport=fallback_sport,
        quick_limit=quick_limit, progress_callback=progress_callback,
    )

    qualified_quick_rows = [
        row for row in (quick.get("rows") or [])
        if assess_seller_card_merit(row)["eligible"]
    ]
    candidates = select_dynamic_seller_deep_rows(
        qualified_quick_rows,
        base_limit=max(int(full_limit or 8), 8),
        max_cap=15,
    )
    candidate_limit = len(candidates)
    full_rows = []
    failed = 0
    _emit(progress_callback, phase="full_start", done=0, total=len(candidates), percent=66)
    for idx, qrow in enumerate(candidates, start=1):
        source_item = qrow.get("source_item") or {}
        if not seller_item_domain_check(source_item, sport="all").get("allowed"):
            continue
        item_sport = qrow.get("sport") or _supported_sport(source_item, fallback=fallback_sport)
        try:
            row = full_analyze_live_seller_item(
                source_item, analyze_fn=analyze_fn, all_items=inventory,
                sport=item_sport, strategy_mode="quick_flip",
            )
        except Exception:
            failed += 1
            row = None
        if row is not None:
            row = dict(row)
            row["quick_score"] = qrow.get("quick_score")
            row["collector_signal_score"] = qrow.get("collector_signal_score", 0)
            row["collector_signals"] = list(qrow.get("collector_signals") or [])
            row["seller_opportunity_score"] = _seller_opportunity_score(row)
            row["seller"] = alias
            row["sport"] = item_sport
            row["analysis_level"] = "full"
            row["seller_card_merit"] = assess_seller_card_merit(row)
            row["deal_readiness"] = assess_deal_readiness(row)
            full_rows.append(_seller_presentation_label(row))
        _emit(progress_callback, phase="full_progress", done=idx, total=len(candidates), percent=66 + int(28 * idx / max(1, len(candidates))))

    full_rows.sort(key=_seller_opportunity_rank_key, reverse=True)
    selected, duplicate_opportunities_removed, condition_risks_demoted = _select_diverse_rows(full_rows, 5)
    selected_keys = {_identity_key(row.get("source_item") or row) for row in selected}
    selected_opportunities = {_card_opportunity_key(row) for row in selected}
    for qrow in qualified_quick_rows:
        if len(selected) >= 5:
            break
        source = qrow.get("source_item") or {}
        if not seller_item_domain_check(source, sport="all").get("allowed"):
            continue
        key = _identity_key(source or qrow)
        fallback = _fallback_row(qrow, alias)
        opportunity_key = _card_opportunity_key(fallback)
        if key in selected_keys or opportunity_key in selected_opportunities or _explicit_condition_risk(fallback):
            continue
        selected.append(fallback)
        selected_keys.add(key)
        selected_opportunities.add(opportunity_key)

    _emit(progress_callback, phase="ranking", done=len(selected), total=5, percent=97)
    common_meta = {
        "seller": alias,
        "inventory_count": len(raw_inventory),
        "card_inventory_count": len(inventory),
        "domain_rejected_count": len(rejected) + int(quick.get("domain_rejected_count") or 0),
        "inventory_unique_count": int(quick.get("inventory_unique_count") or 0),
        "quick_analysed": int(quick.get("analysed_count") or 0),
        "fast_pool_count": int(quick.get("fast_pool_count") or 0),
        "quick_failed": int(quick.get("failed_count") or 0),
        "quick_batches": int(quick.get("batch_count") or 0),
        "coverage_complete": bool(quick.get("coverage_complete")),
        "full_candidate_limit": candidate_limit,
        "ranking_source": "ORDINARY_FLIPFYND_RANK",
        "seller_analysis_contract": "v3-ordinary-evidence-opportunity-overlay",
        "seller_workflow_version": "v3-cross-sport-one-click-progress",
        "sport_counts": quick.get("sport_counts") or {},
        "duplicate_opportunities_removed": duplicate_opportunities_removed,
        "condition_risks_demoted": condition_risks_demoted,
    }
    result = {"status": "READY" if selected else "NO_CARD_CANDIDATES",
              "rows": selected, "full_analysed": len(full_rows), "failed_full": failed,
              **common_meta}
    _emit(progress_callback, phase="complete", done=5 if selected else 0, total=5, percent=100)
    return result
