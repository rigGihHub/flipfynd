"""Local-market fallback for Seller Top 5 when live Tradera inventory is unavailable.

The fallback is intentionally conservative: it only reuses already-loaded listings
whose seller alias can be recovered explicitly. It never invents seller identity,
SOLD evidence, market value or a BUY decision.
"""
from __future__ import annotations

from typing import Callable, Iterable

# Deployment compatibility guard: Streamlit Cloud may briefly run a mixed/stale
# module set during redeploy. Seller Top 5 must degrade safely instead of taking
# down the whole app if the newer backfill helper is not present yet.
try:
    from src.seller_identity import backfill_seller_metadata, seller_alias
except ImportError:
    from src.seller_identity import seller_alias

    def backfill_seller_metadata(items) -> list[dict]:
        """Safe compatibility fallback for older seller_identity deployments.

        No metadata is invented or copied between listings here. Existing seller
        fields are merely preserved until the full canonical backfill helper is
        available in the deployed module set.
        """
        return [dict(x) for x in (items or []) if isinstance(x, dict)]

from src.seller_top5 import build_seller_top5


def _alias_key(value) -> str:
    return str(value or "").strip().casefold()


def local_inventory_for_seller(seller: str, market_items: Iterable[dict] | None) -> list[dict]:
    """Return locally loaded listings that explicitly resolve to ``seller``.

    Seller metadata is first backfilled across safely matched copies of the same
    listing when the canonical helper is available. Matching is then exact after
    trimming/case-folding; partial aliases are deliberately rejected to avoid
    mixing sellers with similar names.
    """
    wanted = _alias_key(seller)
    if not wanted:
        return []

    enriched = backfill_seller_metadata(market_items or [])
    rows = []
    for item in enriched:
        alias = seller_alias(item)
        if alias and _alias_key(alias) == wanted:
            rows.append(dict(item))
    return rows


def build_local_seller_top5(
    seller: str,
    market_items: Iterable[dict] | None,
    *,
    analyze_fn: Callable,
    sport: str = "hockey",
    quick_limit: int = 60,
    full_limit: int = 10,
) -> dict:
    """Run the normal Seller Top 5 engine on safely identified local inventory."""
    inventory = local_inventory_for_seller(seller, market_items)
    result = build_seller_top5(
        seller,
        inventory,
        analyze_fn=analyze_fn,
        sport=sport,
        quick_limit=quick_limit,
        full_limit=full_limit,
    )
    result = dict(result)
    result["inventory_source"] = "LOCAL_MARKET"
    result["local_market_count"] = len([x for x in (market_items or []) if isinstance(x, dict)])
    result["local_seller_match_count"] = len(inventory)
    return result
