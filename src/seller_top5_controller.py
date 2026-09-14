"""Choose the safest available inventory source for Seller Top 5.

Live Tradera seller inventory is preferred when valid app credentials are
available and the API call succeeds. If credentials are missing or the API call
fails, FlipFynd may fall back to already-loaded local market data. A successful
API response with an empty inventory is authoritative and is not replaced with
potentially stale local listings.
"""
from __future__ import annotations

from typing import Callable, Iterable

from src.seller_top5 import build_seller_top5
from src.seller_top5_fallback import build_local_seller_top5
from src.tradera_seller_inventory import discover_active_seller_inventory


def _credentials_pair(credentials):
    if not credentials:
        return None
    try:
        app_id, app_key = credentials[0], credentials[1]
    except (TypeError, IndexError, KeyError):
        return None
    app_id = str(app_id or "").strip()
    app_key = str(app_key or "").strip()
    if not app_id or not app_key:
        return None
    return app_id, app_key


def resolve_seller_top5(
    seller: str,
    market_items: Iterable[dict] | None,
    *,
    analyze_fn: Callable,
    sport: str = "hockey",
    credentials=None,
    inventory_fetcher: Callable = discover_active_seller_inventory,
    quick_limit: int = 60,
    full_limit: int = 10,
) -> dict:
    """Return Seller Top 5 using API first and conservative local fallback.

    Source semantics are explicit in the result:
    - ``TRADERA_API``: live API succeeded; its inventory is authoritative.
    - ``LOCAL_MARKET``: credentials were unavailable or live API failed.

    The controller never turns local fallback data into stronger evidence than
    the underlying normal Seller Top 5 engine permits.
    """
    alias = str(seller or "").strip()
    local_rows = [dict(x) for x in (market_items or []) if isinstance(x, dict)]
    if not alias:
        return {
            "status": "NO_SELLER",
            "rows": [],
            "seller": None,
            "inventory_count": 0,
            "inventory_source": "NONE",
            "fallback_reason": None,
        }

    creds = _credentials_pair(credentials)
    if creds:
        try:
            fetched = inventory_fetcher(
                seller_alias=alias,
                app_id=creds[0],
                app_key=creds[1],
                category_id=0,
            )
        except Exception as exc:
            fetched = {"ok": False, "status": "FETCH_EXCEPTION", "error": str(exc), "items": []}

        if fetched.get("ok"):
            items = [dict(x) for x in (fetched.get("items") or []) if isinstance(x, dict)]
            result = build_seller_top5(
                alias,
                items,
                analyze_fn=analyze_fn,
                sport=sport,
                quick_limit=quick_limit,
                full_limit=full_limit,
            )
            result = dict(result)
            result["inventory_source"] = "TRADERA_API"
            result["api_status"] = fetched.get("status") or "OK"
            result["fallback_reason"] = None
            result["local_market_count"] = len(local_rows)
            return result

        fallback = build_local_seller_top5(
            alias,
            local_rows,
            analyze_fn=analyze_fn,
            sport=sport,
            quick_limit=quick_limit,
            full_limit=full_limit,
        )
        fallback = dict(fallback)
        fallback["fallback_reason"] = "API_FAILED"
        fallback["api_status"] = fetched.get("status") or "UNKNOWN_API_ERROR"
        if fetched.get("error"):
            fallback["api_error"] = str(fetched.get("error"))
        return fallback

    fallback = build_local_seller_top5(
        alias,
        local_rows,
        analyze_fn=analyze_fn,
        sport=sport,
        quick_limit=quick_limit,
        full_limit=full_limit,
    )
    fallback = dict(fallback)
    fallback["fallback_reason"] = "NO_API_CREDENTIALS"
    fallback["api_status"] = "NOT_CONFIGURED"
    return fallback
