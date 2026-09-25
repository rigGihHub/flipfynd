from __future__ import annotations

import os
from urllib.parse import quote
import requests

from src.public_seller_inventory import parse_profile_url

DEFAULT_PROXY_URL = "https://flipfynd-seller-fetcher.onrender.com"
DEFAULT_PROXY_TIMEOUT_SECONDS = 60


def _proxy_timeout(value=None) -> int:
    """Allow cold-start tolerance without making long hangs unbounded."""
    raw = value if value is not None else os.getenv("FLIPFYND_SELLER_PROXY_TIMEOUT")
    try:
        return max(10, min(120, int(raw))) if raw not in (None, "") else DEFAULT_PROXY_TIMEOUT_SECONDS
    except (TypeError, ValueError):
        return DEFAULT_PROXY_TIMEOUT_SECONDS


def fetch_proxy_seller_inventory_batch(
    profile_url: str,
    *,
    start_page: int = 1,
    max_pages: int = 1,
    timeout: int | None = None,
    progress_callback=None,
    fallback_alias: str | None = None,
) -> dict:
    """Fetch one seller page through the dedicated Render fetcher.

    This exists because Streamlit Cloud can be blocked/reset by Tradera even
    when the same public page is available from a browser-like TLS client.
    The proxy is read-only and only accepts a numeric Tradera seller id.
    """
    parsed = parse_profile_url(profile_url) or {}
    seller_id = str(parsed.get("seller_id") or "").strip()
    if not seller_id.isdigit():
        return {"ok": False, "status": "INVALID_PROFILE_URL", "items": [], "next_page": start_page}
    alias = str(parsed.get("alias") or fallback_alias or "").strip()
    base = str(os.getenv("FLIPFYND_SELLER_PROXY_URL") or DEFAULT_PROXY_URL).rstrip("/")

    request_timeout = _proxy_timeout(timeout)
    page = max(1, int(start_page or 1))
    page_limit = max(1, int(max_pages or 1))
    all_items = {}
    total_estimate = None
    pages_read = 0
    exhausted = False

    for _ in range(page_limit):
        if callable(progress_callback):
            try:
                progress_callback({
                    "phase": "fetching",
                    "page": page,
                    "pages_read": pages_read,
                    "max_pages": page_limit,
                    "found_count": len(all_items),
                    "seller_alias": alias or None,
                })
            except Exception:
                pass
        params = {"page": page}
        if alias:
            params["alias"] = alias
        try:
            response = requests.get(
                f"{base}/seller/{quote(seller_id)}",
                params=params,
                timeout=request_timeout,
            )
        except requests.RequestException as exc:
            return {
                "ok": False,
                "status": "PROXY_TIMEOUT" if isinstance(exc, requests.Timeout) else "PROXY_REQUEST_FAILED",
                "error": str(exc),
                "timeout_seconds": request_timeout,
                "items": list(all_items.values()),
                "next_page": page,
                "pages_read": pages_read,
            }
        if response.status_code != 200:
            detail = None
            try:
                detail = (response.json() or {}).get("detail")
            except Exception:
                detail = response.text[:300]
            return {
                "ok": False,
                "status": "PROXY_HTTP_ERROR",
                "http_status": response.status_code,
                "error": detail or f"proxy http {response.status_code}",
                "diagnostic_code": (
                    detail.get("code") if isinstance(detail, dict)
                    else "FF-SELLER-PROXY-HTTP"
                ),
                "items": list(all_items.values()),
                "next_page": page,
                "pages_read": pages_read,
            }
        try:
            payload = response.json()
        except ValueError:
            return {
                "ok": False,
                "status": "PROXY_INVALID_JSON",
                "items": list(all_items.values()),
                "next_page": page,
                "pages_read": pages_read,
            }
        for item in payload.get("items") or []:
            if isinstance(item, dict):
                key = str(item.get("tradera_item_id") or item.get("lank") or "").strip()
                if key:
                    all_items[key] = item
        if payload.get("total_listing_estimate"):
            total_estimate = int(payload["total_listing_estimate"])
        if payload.get("exhausted") and not (payload.get("items") or []):
            exhausted = True
            page = int(payload.get("next_page") or page)
            break
        pages_read += 1
        page = int(payload.get("next_page") or (page + 1))
        if payload.get("exhausted"):
            exhausted = True
            break

    if callable(progress_callback):
        try:
            progress_callback({
                "phase": "page_complete",
                "page": max(1, page - 1),
                "pages_read": pages_read,
                "max_pages": page_limit,
                "found_count": len(all_items),
                "page_count": len(all_items),
                "seller_alias": alias or None,
            })
        except Exception:
            pass

    return {
        "ok": True,
        "status": "OK",
        "seller": {"seller_id": seller_id, "alias": alias or None},
        "items": list(all_items.values()),
        "parsed_count": len(all_items),
        "pages_read": pages_read,
        "next_page": page,
        "exhausted": exhausted,
        "inventory_source": "TRADERA_RENDER_PROXY",
        "total_listing_estimate": total_estimate,
    }
