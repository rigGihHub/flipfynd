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

    The quick pass searches broadly through the seller inventory. Only the most
    promising candidates are then promoted through the normal full analyser.
    """
    alias = str(seller_alias or "").strip()
    inventory = [dict(x) for x in (items or []) if isinstance(x, dict)]
    if not alias:
        return {"status": "NO_SELLER", "rows": [], "seller": None, "inventory_count": len(inventory)}
    if not inventory:
        return {"status": "NO_ITEMS", "rows": [], "seller": alias, "inventory_count": 0}

    anchor = {"saljare": alias, "tradera_item_id": "__seller_top5_anchor__"}
    quick = quick_analyze_seller_inventory(
        anchor,
        inventory,
        analyze_fn=analyze_fn,
        sport=sport,
        strategy_mode="quick_flip",
        limit=max(5, int(quick_limit)),
        shortlist=max(5, min(int(full_limit), 20)),
    )

    candidates = list(quick.get("rows") or [])[: max(5, min(int(full_limit), 20))]
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
            "seller": alias,
            "inventory_count": len(inventory),
            "quick_analysed": int(quick.get("analysed_count") or 0),
            "full_analysed": 0,
            "failed_full": failed,
        }

    full_rows.sort(key=_rank_key)
    return {
        "status": "READY",
        "rows": full_rows[:5],
        "seller": alias,
        "inventory_count": len(inventory),
        "quick_analysed": int(quick.get("analysed_count") or 0),
        "full_analysed": len(full_rows),
        "failed_full": failed,
    }
