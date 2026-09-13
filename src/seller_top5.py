"""Rank the best current FlipFynd opportunities from one Tradera seller.

This is seller-scoped discovery. It reuses the existing quick/full analysis stack
and never invents BUY, market value or SOLD evidence. A seller Top 5 may contain
research candidates when no verified BUY exists, but they are labelled clearly.
"""
from __future__ import annotations

from typing import Callable, Iterable

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


def _rank_key(row: dict):
    decision = str(row.get("decision") or "").upper()
    is_buy = decision.startswith("KÖP")
    sold = int(_num(row.get("sold_comps")))
    identity_ok = bool(row.get("identity_ok"))
    edge = _num(row.get("market_edge"))
    valuation = _num(row.get("valuation_confidence"))
    quick = _num(row.get("quick_score"))
    price = row.get("price")
    try:
        price = float(price)
    except (TypeError, ValueError):
        price = 10**12
    return (
        0 if is_buy else 1,
        0 if identity_ok and sold >= 2 else 1,
        -sold,
        -edge,
        -valuation,
        -quick,
        price,
    )


def _quick_rank_key(row: dict):
    decision = str(row.get("decision") or "").upper()
    sold = int(_num(row.get("sold_comps")))
    identity_ok = bool(row.get("identity_ok"))
    return (
        0 if decision.startswith("KÖP") else 1,
        0 if identity_ok and sold > 0 else 1,
        -sold,
        -_num(row.get("market_edge")),
        -_num(row.get("valuation_confidence")),
        -_num(row.get("quick_score")),
        _num(row.get("price"), 10**12),
    )


def _quick_scan_inventory(
    alias: str,
    inventory: list[dict],
    *,
    analyze_fn: Callable,
    sport: str,
    quick_limit: int,
) -> dict:
    """Quick-scan the seller inventory in bounded batches.

    Older behaviour sent the whole inventory to one quick-analysis call, whose
    internal cap meant a seller with hundreds of listings could have large parts
    of the shop ignored. This scans every unique listing in batches while keeping
    each individual analysis call bounded. Full analysis is still reserved for
    only the strongest candidates.
    """
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
    for start in range(0, len(unique_inventory), batch_size):
        batch = unique_inventory[start : start + batch_size]
        if not batch:
            continue
        batches += 1
        quick = quick_analyze_seller_inventory(
            anchor,
            batch,
            analyze_fn=analyze_fn,
            sport=sport,
            strategy_mode="quick_flip",
            limit=len(batch),
            shortlist=min(5, len(batch)),
        )
        failed += int(quick.get("failed_count") or 0)
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
        "inventory_unique_count": len(unique_inventory),
        "coverage_complete": len(rows) + failed >= len(unique_inventory),
    }


def build_seller_top5(
    seller_alias: str,
    items: Iterable[dict] | None,
    *,
    analyze_fn: Callable,
    sport: str = "hockey",
    quick_limit: int = 60,
    full_limit: int = 10,
) -> dict:
    """Return the five best seller-scoped opportunities.

    The quick pass now adapts to inventory size and scans the full unique seller
    inventory in bounded batches. Only the strongest candidates are then
    promoted through the normal full analyser, so a strong card late in a large
    seller inventory cannot be missed solely because it fell outside the first
    60 listings.
    """
    alias = str(seller_alias or "").strip()
    inventory = [dict(x) for x in (items or []) if isinstance(x, dict)]
    if not alias:
        return {"status": "NO_SELLER", "rows": [], "seller": None, "inventory_count": len(inventory)}
    if not inventory:
        return {"status": "NO_ITEMS", "rows": [], "seller": alias, "inventory_count": 0}

    quick = _quick_scan_inventory(
        alias,
        inventory,
        analyze_fn=analyze_fn,
        sport=sport,
        quick_limit=quick_limit,
    )

    candidate_limit = max(5, min(int(full_limit), 20))
    candidates = list(quick.get("rows") or [])[:candidate_limit]
    full_rows = []
    failed = 0
    for qrow in candidates:
        source_item = qrow.get("source_item") or {}
        try:
            full = full_analyze_live_seller_item(
                source_item,
                analyze_fn=analyze_fn,
                all_items=inventory,
                sport=sport,
                strategy_mode="quick_flip",
            )
        except Exception:
            failed += 1
            continue
        row = dict(full)
        row["quick_score"] = qrow.get("quick_score")
        row["seller"] = alias
        full_rows.append(row)

    common_meta = {
        "seller": alias,
        "inventory_count": len(inventory),
        "inventory_unique_count": int(quick.get("inventory_unique_count") or 0),
        "quick_analysed": int(quick.get("analysed_count") or 0),
        "quick_failed": int(quick.get("failed_count") or 0),
        "quick_batches": int(quick.get("batch_count") or 0),
        "coverage_complete": bool(quick.get("coverage_complete")),
    }

    # If the full pass fails entirely, fall back to clearly labelled quick research
    # candidates instead of pretending that no seller inventory exists.
    if not full_rows:
        fallback = []
        for qrow in list(quick.get("rows") or [])[:5]:
            fallback.append({
                "title": qrow.get("title"),
                "price": qrow.get("price"),
                "url": qrow.get("url"),
                "decision": "UNDERSÖK",
                "label": "SNABBANALYS – BEHÖVER VERIFIERAS",
                "reason": qrow.get("reason") or "Full analys kunde inte slutföras.",
                "identity_ok": qrow.get("identity_ok"),
                "sold_comps": qrow.get("sold_comps", 0),
                "valuation_confidence": qrow.get("valuation_confidence", 0),
                "market_edge": qrow.get("market_edge", 0),
                "quick_score": qrow.get("quick_score", 0),
                "seller": alias,
                "source_item": qrow.get("source_item") or {},
            })
        return {
            "status": "QUICK_ONLY" if fallback else "NO_RESULTS",
            "rows": fallback,
            "full_analysed": 0,
            "failed_full": failed,
            **common_meta,
        }

    full_rows.sort(key=_rank_key)
    return {
        "status": "READY",
        "rows": full_rows[:5],
        "full_analysed": len(full_rows),
        "failed_full": failed,
        **common_meta,
    }
