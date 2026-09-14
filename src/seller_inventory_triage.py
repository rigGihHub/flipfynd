"""Two-stage triage for large imported seller inventories.

Every safely seller-matched local listing is considered in the cheap pre-sort.
Only the strongest bounded subset is sent through the existing fast analyser,
then the best research candidates are returned. This is a research router, not
a BUY engine.
"""
from __future__ import annotations

from typing import Callable, Iterable

from src.seller_top5_fallback import local_inventory_for_seller
from src.seller_live_quick_analysis import quick_analyze_seller_inventory


def build_seller_inventory_triage(
    seller: str,
    market_items: Iterable[dict] | None,
    *,
    analyze_fn: Callable,
    sport: str = "hockey",
    max_fast_analyses: int = 120,
    top_n: int = 20,
) -> dict:
    """Scan all locally loaded seller listings and return the best research set.

    ``quick_analyze_seller_inventory`` already performs a cheap deterministic
    pre-sort before running the fast analyser. We therefore pass the complete
    safely matched seller inventory into it and bound only the expensive stage.
    """
    inventory = local_inventory_for_seller(seller, market_items)
    if not inventory:
        return {
            "status": "NO_INVENTORY",
            "seller": str(seller or "").strip() or None,
            "inventory_count": 0,
            "cheap_scanned_count": 0,
            "fast_analysed_count": 0,
            "failed_count": 0,
            "rows": [],
            "top_n": int(max(1, top_n)),
            "note": "Ingen säkert säljaridentifierad lokal annons finns ännu.",
        }

    # There is no anchor listing in this workflow; an impossible synthetic key
    # prevents accidental exclusion of a real listing.
    anchor = {"tradera_item_id": "__seller_inventory_triage_anchor__"}
    quick = quick_analyze_seller_inventory(
        anchor,
        inventory,
        analyze_fn=analyze_fn,
        sport=sport,
        limit=max(1, int(max_fast_analyses)),
        shortlist=5,
    )
    rows = list(quick.get("rows") or [])[: max(1, int(top_n))]
    return {
        "status": "READY" if rows else "NO_RESULTS",
        "seller": str(seller or "").strip() or None,
        "inventory_count": len(inventory),
        "cheap_scanned_count": len(inventory),
        "fast_analysed_count": int(quick.get("analysed_count") or 0),
        "failed_count": int(quick.get("failed_count") or 0),
        "rows": rows,
        "top_n": max(1, int(top_n)),
        "note": (
            "Alla säkert matchade annonser skannas billigt. Bara den starkaste "
            "begränsade delmängden snabb-analyseras. Resultatet är UNDERSÖK-prioritering, "
            "inte en köporder."
        ),
    }
