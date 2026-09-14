"""Choose the safest available inventory source for Seller Top 5.

One click owns the whole seller workflow: fetch inventory, filter non-cards,
triage supported sports, full-analyse the strongest candidates and return one
cross-sport Top 5. Live Tradera API is preferred; public profile is next; local
market data is the conservative fallback.
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


class _SellerProgress:
    """Best-effort Streamlit progress UI; inert in tests/non-Streamlit callers."""
    def __init__(self):
        self.bar = None
        try:
            import streamlit as st
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            if get_script_run_ctx() is not None:
                self.bar = st.progress(0, text="Steg 1/5 · Hämtar säljarens annonser…")
        except Exception:
            self.bar = None

    def update(self, payload):
        if self.bar is None:
            return
        info = dict(payload or {})
        phase = str(info.get("phase") or "")
        percent = info.get("percent")
        if percent is None:
            if phase in {"starting", "fetching", "page_complete", "exhausted"}:
                read = int(info.get("pages_read") or 0)
                maximum = max(1, int(info.get("max_pages") or 1))
                percent = min(20, 2 + int(18 * read / maximum))
            elif phase == "complete":
                percent = 100
            else:
                percent = 1
        percent = max(0, min(100, int(percent)))
        done = int(info.get("done") or 0)
        total = int(info.get("total") or 0)
        found = int(info.get("found_count") or 0)
        if phase in {"starting", "fetching", "page_complete", "exhausted"}:
            page = int(info.get("page") or 0)
            text = f"Steg 1/5 · Hämtar annonser · sida {page} · {found} hittade"
        elif phase.startswith("filter"):
            text = f"Steg 2/5 · Filtrerar till samlarkort · {done}/{total}" if total else "Steg 2/5 · Filtrerar till samlarkort…"
        elif phase.startswith("quick"):
            text = f"Steg 3/5 · Snabbanalyserar och prioriterar · {done}/{total}" if total else "Steg 3/5 · Snabbanalyserar…"
        elif phase.startswith("full"):
            text = f"Steg 4/5 · Fullanalyserar starkaste kandidaterna · {done}/{total}" if total else "Steg 4/5 · Fullanalyserar…"
        elif phase == "ranking":
            text = "Steg 5/5 · Rankar säljarens fem bästa fynd…"
        elif phase == "complete":
            text = "Klart · säljarens Top 5 är rankad"
        else:
            text = "Bearbetar säljarens annonser…"
        try:
            self.bar.progress(percent, text=text)
        except Exception:
            pass


def _emit(callback, ui, payload):
    ui.update(payload)
    if callable(callback):
        try:
            callback(dict(payload or {}))
        except Exception:
            pass


def _rank(alias, items, *, analyze_fn, quick_limit, full_limit, source, progress_callback=None, ui=None):
    ui = ui or _SellerProgress()

    def combined_progress(payload):
        _emit(progress_callback, ui, payload)

    result = build_seller_top5(
        alias,
        [dict(x) for x in (items or []) if isinstance(x, dict)],
        analyze_fn=analyze_fn,
        sport="all",
        quick_limit=quick_limit,
        full_limit=full_limit,
        progress_callback=combined_progress,
    )
    result = dict(result)
    result["inventory_source"] = source
    return result


def _fetch_public(public_fetcher, profile_url, *, public_pages, progress_callback=None, seller_alias=None):
    kwargs = {"start_page": 1, "max_pages": max(1, int(public_pages or 1))}
    if progress_callback is not None:
        kwargs["progress_callback"] = progress_callback
    if str(seller_alias or "").strip():
        kwargs["fallback_alias"] = str(seller_alias).strip()

    for optional_key in ("fallback_alias", "progress_callback"):
        try:
            return public_fetcher(str(profile_url).strip(), **kwargs)
        except TypeError as exc:
            if optional_key not in str(exc) or optional_key not in kwargs:
                if optional_key == "progress_callback":
                    raise
                continue
            kwargs.pop(optional_key, None)
    return public_fetcher(str(profile_url).strip(), **kwargs)


def resolve_seller_top5(
    seller: str,
    market_items: Iterable[dict] | None,
    *,
    analyze_fn: Callable,
    sport: str = "all",
    credentials=None,
    profile_url: str | None = None,
    inventory_fetcher: Callable = discover_active_seller_inventory,
    public_fetcher: Callable = fetch_public_seller_inventory_batch,
    quick_limit: int = 60,
    full_limit: int = 10,
    public_pages: int = 120,
    progress_callback=None,
) -> dict:
    alias = str(seller or "").strip()
    local_rows = [dict(x) for x in (market_items or []) if isinstance(x, dict)]
    if not alias:
        return {"status": "NO_SELLER", "rows": [], "seller": None,
                "inventory_count": 0, "inventory_source": "NONE", "fallback_reason": None}

    ui = _SellerProgress()

    def combined_progress(payload):
        _emit(progress_callback, ui, payload)

    creds = _credentials_pair(credentials)
    api_failure = None
    if creds:
        combined_progress({"phase": "starting", "page": 1, "pages_read": 0, "max_pages": 1, "found_count": 0, "percent": 2})
        try:
            fetched = inventory_fetcher(
                seller_alias=alias, app_id=creds[0], app_key=creds[1], category_id=0,
            )
        except Exception as exc:
            fetched = {"ok": False, "status": "FETCH_EXCEPTION", "error": str(exc), "items": []}
        if fetched.get("ok"):
            items = fetched.get("items") or []
            combined_progress({"phase": "page_complete", "page": 1, "pages_read": 1, "max_pages": 1, "found_count": len(items), "percent": 20})
            result = _rank(
                alias, items, analyze_fn=analyze_fn, quick_limit=quick_limit,
                full_limit=full_limit, source="TRADERA_API",
                progress_callback=progress_callback, ui=ui,
            )
            result["api_status"] = fetched.get("status") or "OK"
            result["fallback_reason"] = None
            result["local_market_count"] = len(local_rows)
            return result
        api_failure = fetched

    public_failure = None
    if str(profile_url or "").strip():
        try:
            public = _fetch_public(
                public_fetcher, profile_url, public_pages=public_pages,
                progress_callback=combined_progress, seller_alias=alias,
            )
        except Exception as exc:
            public = {"ok": False, "status": "FETCH_EXCEPTION", "error": str(exc), "items": []}
        if public.get("ok") and (public.get("items") or []):
            result = _rank(
                alias, public.get("items") or [], analyze_fn=analyze_fn,
                quick_limit=quick_limit, full_limit=full_limit,
                source="TRADERA_PUBLIC_PROFILE", progress_callback=progress_callback, ui=ui,
            )
            result["public_status"] = public.get("status") or "OK"
            result["public_pages_read"] = int(public.get("pages_read") or 0)
            result["public_inventory_complete"] = bool(public.get("exhausted"))
            result["fallback_reason"] = "NO_API_CREDENTIALS" if not creds else "API_FAILED"
            result["api_status"] = (api_failure or {}).get("status") if api_failure else ("NOT_CONFIGURED" if not creds else "OK")
            return result
        public_failure = public

    # Preserve the seller-scoped local fallback contract and metadata. The local
    # helper filters exact seller identity before invoking the same Top 5 engine.
    combined_progress({"phase": "filter_start", "done": 0, "total": len(local_rows), "percent": 20})
    result = build_local_seller_top5(
        alias,
        local_rows,
        analyze_fn=analyze_fn,
        sport="all",
        quick_limit=quick_limit,
        full_limit=full_limit,
    )
    result = dict(result)
    combined_progress({"phase": "complete", "done": len(result.get("rows") or []), "total": 5, "percent": 100})
    if creds and api_failure:
        result["fallback_reason"] = "API_FAILED"
        result["api_status"] = api_failure.get("status") or "UNKNOWN_API_ERROR"
        if api_failure.get("error"):
            result["api_error"] = str(api_failure.get("error"))
    else:
        result["fallback_reason"] = "NO_API_CREDENTIALS"
        result["api_status"] = "NOT_CONFIGURED"
    if public_failure:
        result["public_status"] = public_failure.get("status") or "UNKNOWN_PUBLIC_ERROR"
    return result
