"""Choose the safest available inventory source for Seller Top 5.

Live Tradera seller inventory is preferred when valid app credentials are
available. A supplied public seller-profile URL is the second discovery path.
Already-loaded local market data remains the final conservative fallback.
"""
from __future__ import annotations

from typing import Callable, Iterable

from src.public_seller_inventory import fetch_public_seller_inventory_batch
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


def _rank(alias, items, *, analyze_fn, sport, quick_limit, full_limit, source):
    result = build_seller_top5(
        alias,
        [dict(x) for x in (items or []) if isinstance(x, dict)],
        analyze_fn=analyze_fn,
        sport=sport,
        quick_limit=quick_limit,
        full_limit=full_limit,
    )
    result = dict(result)
    result["inventory_source"] = source
    return result


def resolve_seller_top5(
    seller: str,
    market_items: Iterable[dict] | None,
    *,
    analyze_fn: Callable,
    sport: str = "hockey",
    credentials=None,
    profile_url: str | None = None,
    inventory_fetcher: Callable = discover_active_seller_inventory,
    public_fetcher: Callable = fetch_public_seller_inventory_batch,
    quick_limit: int = 60,
    full_limit: int = 10,
    public_pages: int = 12,
) -> dict:
    """Return Seller Top 5 using API -> public profile -> local fallback.

    A successful API response, including an empty result, is authoritative.
    Public-profile inventory is discovery data only and does not become SOLD
    evidence or a stronger buy signal by virtue of its source.
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
    api_failure = None
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
            result = _rank(
                alias, fetched.get("items") or [], analyze_fn=analyze_fn, sport=sport,
                quick_limit=quick_limit, full_limit=full_limit, source="TRADERA_API",
            )
            result["api_status"] = fetched.get("status") or "OK"
            result["fallback_reason"] = None
            result["local_market_count"] = len(local_rows)
            return result
        api_failure = fetched

    public_failure = None
    if str(profile_url or "").strip():
        try:
            public = public_fetcher(
                str(profile_url).strip(), start_page=1, max_pages=max(1, int(public_pages or 1))
            )
        except Exception as exc:
            public = {"ok": False, "status": "FETCH_EXCEPTION", "error": str(exc), "items": []}
        if public.get("ok") and (public.get("items") or []):
            result = _rank(
                alias, public.get("items") or [], analyze_fn=analyze_fn, sport=sport,
                quick_limit=quick_limit, full_limit=full_limit, source="TRADERA_PUBLIC_PROFILE",
            )
            result["public_status"] = public.get("status") or "OK"
            result["public_pages_read"] = int(public.get("pages_read") or 0)
            result["fallback_reason"] = "NO_API_CREDENTIALS" if not creds else "API_FAILED"
            result["api_status"] = (api_failure or {}).get("status") if api_failure else ("NOT_CONFIGURED" if not creds else "OK")
            return result
        public_failure = public

    fallback = build_local_seller_top5(
        alias,
        local_rows,
        analyze_fn=analyze_fn,
        sport=sport,
        quick_limit=quick_limit,
        full_limit=full_limit,
    )
    fallback = dict(fallback)
    if creds and api_failure:
        fallback["fallback_reason"] = "API_FAILED"
        fallback["api_status"] = api_failure.get("status") or "UNKNOWN_API_ERROR"
        if api_failure.get("error"):
            fallback["api_error"] = str(api_failure.get("error"))
    else:
        fallback["fallback_reason"] = "NO_API_CREDENTIALS"
        fallback["api_status"] = "NOT_CONFIGURED"
    if public_failure:
        fallback["public_status"] = public_failure.get("status") or "UNKNOWN_PUBLIC_ERROR"
    return fallback
