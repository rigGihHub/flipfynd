"""Rank the best current FlipFynd card candidates from one Tradera seller.

Seller-specific logic is deliberately limited to inventory filtering and cheap
triage. Final decisions and final ordering reuse the normal FlipFynd full
analysis contract: rank_score, player_market_score, risk_adjusted_profit.
"""
from __future__ import annotations

from typing import Callable, Iterable

from src.seller_card_domain import seller_item_domain_check
from src.seller_live_quick_analysis import quick_analyze_seller_inventory
from src.seller_live_full_analysis import full_analyze_live_seller_item


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


def _ordinary_rank_key(row: dict):
    """Mirror the ordinary result ordering in app.py, descending."""
    return (
        _num(row.get("rank_score")),
        _num(row.get("player_market_score")),
        _num(row.get("risk_adjusted_profit")),
    )


def _quick_rank_key(row: dict):
    """Preselect using ordinary fast-analysis ranking fields first."""
    decision = str(row.get("decision") or "").upper()
    sold = int(_num(row.get("sold_comps")))
    identity_ok = bool(row.get("identity_ok"))
    return (
        -_num(row.get("rank_score")),
        -_num(row.get("player_market_score")),
        -_num(row.get("risk_adjusted_profit")),
        0 if decision.startswith("KÖP") else 1,
        0 if identity_ok and sold > 0 else 1,
        -sold,
        -_num(row.get("quick_score")),
        -_num(row.get("collector_signal_score")),
        _num(row.get("price"), 10**12),
    )


def _seller_presentation_label(row: dict) -> dict:
    """Map ordinary decisions to Seller Top 5 presentation only."""
    out = dict(row)
    decision = str(out.get("decision") or "SKIP").upper()
    if decision.startswith("KÖP"):
        out["label"] = "KÖP-KANDIDAT"
    elif decision.startswith("UNDERSÖK"):
        out["label"] = "VÄRT ATT UNDERSÖKA"
    else:
        out["label"] = "BÄST AV RESTEN"
    return out


def _quick_scan_inventory(alias: str, inventory: list[dict], *, analyze_fn: Callable, sport: str, quick_limit: int) -> dict:
    anchor = {"saljare": alias, "tradera_item_id": "__seller_top5_anchor__"}
    batch_size = max(20, min(int(quick_limit or 60), 100))
    unique: dict[str, dict] = {}
    for row in inventory:
        key = _identity_key(row)
        if key:
            unique[key] = row
    unique_inventory = list(unique.values())

    all_rows: dict[str, dict] = {}
    failed = 0
    batches = 0
    domain_rejected = 0
    for start in range(0, len(unique_inventory), batch_size):
        batch = unique_inventory[start:start + batch_size]
        if not batch:
            continue
        batches += 1
        quick = quick_analyze_seller_inventory(
            anchor, batch, analyze_fn=analyze_fn, sport=sport,
            strategy_mode="quick_flip", limit=len(batch), shortlist=min(5, len(batch)),
        )
        failed += int(quick.get("failed_count") or 0)
        domain_rejected += int(quick.get("domain_rejected_count") or 0)
        for row in quick.get("rows") or []:
            source = row.get("source_item") or {}
            key = _identity_key(source) or _identity_key(row)
            if not key:
                continue
            previous = all_rows.get(key)
            if previous is None or _quick_rank_key(row) < _quick_rank_key(previous):
                all_rows[key] = row

    rows = list(all_rows.values())
    rows.sort(key=_quick_rank_key)
    return {
        "rows": rows,
        "analysed_count": len(rows),
        "failed_count": failed,
        "batch_count": batches,
        "domain_rejected_count": domain_rejected,
        "inventory_unique_count": len(unique_inventory),
        "coverage_complete": len(rows) + failed + domain_rejected >= len(unique_inventory),
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
        "rank_score": qrow.get("rank_score", 0),
        "player_market_score": qrow.get("player_market_score", 0),
        "risk_adjusted_profit": qrow.get("risk_adjusted_profit", 0),
        "seller": alias, "source_item": qrow.get("source_item") or {},
        "analysis_level": "quick_fallback",
    }


def build_seller_top5(seller_alias: str, items: Iterable[dict] | None, *, analyze_fn: Callable,
                      sport: str = "hockey", quick_limit: int = 60, full_limit: int = 10) -> dict:
    alias = str(seller_alias or "").strip()
    raw_inventory = [dict(x) for x in (items or []) if isinstance(x, dict)]
    if not alias:
        return {"status": "NO_SELLER", "rows": [], "seller": None, "inventory_count": len(raw_inventory)}
    if not raw_inventory:
        return {"status": "NO_ITEMS", "rows": [], "seller": alias, "inventory_count": 0}

    rejected = []
    inventory = []
    for item in raw_inventory:
        check = seller_item_domain_check(item, sport=sport)
        if check.get("allowed"):
            inventory.append(item)
        else:
            rejected.append({"title": check.get("title"), "reason": check.get("reason")})

    if not inventory:
        return {
            "status": "NO_CARD_ITEMS", "rows": [], "seller": alias,
            "inventory_count": len(raw_inventory), "card_inventory_count": 0,
            "domain_rejected_count": len(rejected),
        }

    quick = _quick_scan_inventory(alias, inventory, analyze_fn=analyze_fn, sport=sport, quick_limit=quick_limit)

    candidate_limit = min(max(int(full_limit or 20), 20), 40)
    candidates = list(quick.get("rows") or [])[:candidate_limit]
    full_rows = []
    failed = 0
    for qrow in candidates:
        source_item = qrow.get("source_item") or {}
        # Defense in depth: never full-analyse a non-card candidate even if stale
        # or malformed cached data slipped into the quick layer.
        if not seller_item_domain_check(source_item, sport=sport).get("allowed"):
            continue
        try:
            row = full_analyze_live_seller_item(
                source_item, analyze_fn=analyze_fn, all_items=inventory,
                sport=sport, strategy_mode="quick_flip",
            )
        except Exception:
            failed += 1
            continue
        row = dict(row)
        row["quick_score"] = qrow.get("quick_score")
        row["seller"] = alias
        row["analysis_level"] = "full"
        full_rows.append(_seller_presentation_label(row))

    full_rows.sort(key=_ordinary_rank_key, reverse=True)
    selected = list(full_rows[:5])

    selected_keys = {_identity_key(row.get("source_item") or row) for row in selected}
    for qrow in quick.get("rows") or []:
        if len(selected) >= 5:
            break
        source = qrow.get("source_item") or {}
        if not seller_item_domain_check(source, sport=sport).get("allowed"):
            continue
        key = _identity_key(source or qrow)
        if key in selected_keys:
            continue
        selected.append(_fallback_row(qrow, alias))
        selected_keys.add(key)

    common_meta = {
        "seller": alias,
        "inventory_count": len(raw_inventory),
        "card_inventory_count": len(inventory),
        "domain_rejected_count": len(rejected) + int(quick.get("domain_rejected_count") or 0),
        "inventory_unique_count": int(quick.get("inventory_unique_count") or 0),
        "quick_analysed": int(quick.get("analysed_count") or 0),
        "quick_failed": int(quick.get("failed_count") or 0),
        "quick_batches": int(quick.get("batch_count") or 0),
        "coverage_complete": bool(quick.get("coverage_complete")),
        "full_candidate_limit": candidate_limit,
        "ranking_source": "ORDINARY_FLIPFYND_RANK",
        "seller_analysis_contract": "v2-ordinary-rank-preselection",
    }
    return {
        "status": "READY" if selected else "NO_CARD_CANDIDATES",
        "rows": selected, "full_analysed": len(full_rows), "failed_full": failed,
        **common_meta,
    }
