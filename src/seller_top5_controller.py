"""Choose the safest available inventory source for Seller Top 5.

One click owns the whole seller workflow. Public Tradera profiles are read in
small checkpointed batches so Streamlit never needs to keep one very long
request alive. Ranking starts only after the complete public inventory has been
collected.
"""
from __future__ import annotations

from typing import Callable, Iterable

from src.public_seller_inventory import fetch_public_seller_inventory_batch
from src.seller_top5 import build_seller_top5
from src.seller_top5_fallback import local_inventory_for_seller
from src.tradera_seller_inventory import discover_active_seller_inventory

PUBLIC_BATCH_PAGES = 10


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
    """Best-effort Streamlit progress UI; inert when an external callback owns UI."""
    def __init__(self, enabled: bool = True):
        self.bar = None
        if not enabled:
            return
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
    ui = ui or _SellerProgress(enabled=progress_callback is None)

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


def _fetch_public(public_fetcher, profile_url, *, start_page, public_pages, progress_callback=None, seller_alias=None):
    kwargs = {
        "start_page": max(1, int(start_page or 1)),
        "max_pages": max(1, int(public_pages or 1)),
    }
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


def _streamlit_session_state():
    """Return Streamlit session_state only inside a real app run."""
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is not None:
            return st.session_state
    except Exception:
        pass
    return None


def _checkpoint_key(alias: str, profile_url: str) -> str:
    return "seller_public_checkpoint::" + str(alias or "").strip().casefold() + "::" + str(profile_url or "").strip()


def _item_key(item: dict) -> str:
    return str(
        item.get("tradera_item_id")
        or item.get("item_id")
        or item.get("id")
        or item.get("lank")
        or item.get("url")
        or item.get("titel")
        or item.get("title")
        or ""
    ).strip()


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

    ui = _SellerProgress(enabled=progress_callback is None)

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
    profile_text = str(profile_url or "").strip()
    if profile_text:
        session = _streamlit_session_state()
        key = _checkpoint_key(alias, profile_text)
        checkpoint = None
        if session is not None:
            checkpoint = session.get(key)
        if not isinstance(checkpoint, dict):
            checkpoint = {"next_page": 1, "pages_read": 0, "items": {}}

        start_page = max(1, int(checkpoint.get("next_page") or 1))
        stored_items = dict(checkpoint.get("items") or {})
        batch_pages = min(PUBLIC_BATCH_PAGES, max(1, int(public_pages or PUBLIC_BATCH_PAGES)))

        try:
            public = _fetch_public(
                public_fetcher,
                profile_text,
                start_page=start_page,
                public_pages=batch_pages,
                progress_callback=combined_progress,
                seller_alias=alias,
            )
        except Exception as exc:
            public = {"ok": False, "status": "FETCH_EXCEPTION", "error": str(exc), "items": []}

        if public.get("ok"):
            for item in public.get("items") or []:
                if isinstance(item, dict):
                    k = _item_key(item)
                    if k:
                        stored_items[k] = dict(item)
            total_pages_read = int(checkpoint.get("pages_read") or 0) + int(public.get("pages_read") or 0)
            next_page = int(public.get("next_page") or (start_page + batch_pages))
            exhausted = bool(public.get("exhausted"))

            if not exhausted:
                if session is not None:
                    session[key] = {
                        "next_page": next_page,
                        "pages_read": total_pages_read,
                        "items": stored_items,
                    }
                return {
                    "status": "INVENTORY_PARTIAL",
                    "seller": alias,
                    "rows": [],
                    "inventory_count": len(stored_items),
                    "inventory_source": "TRADERA_PUBLIC_PROFILE",
                    "public_status": public.get("status") or "OK",
                    "public_pages_read": total_pages_read,
                    "public_next_page": next_page,
                    "public_batch_pages": int(public.get("pages_read") or 0),
                    "public_inventory_complete": False,
                    "fallback_reason": "NO_API_CREDENTIALS" if not creds else "API_FAILED",
                    "api_status": (api_failure or {}).get("status") if api_failure else ("NOT_CONFIGURED" if not creds else "OK"),
                }

            if session is not None:
                try:
                    del session[key]
                except Exception:
                    pass

            result = _rank(
                alias,
                list(stored_items.values()),
                analyze_fn=analyze_fn,
                quick_limit=quick_limit,
                full_limit=full_limit,
                source="TRADERA_PUBLIC_PROFILE",
                progress_callback=progress_callback,
                ui=ui,
            )
            result["public_status"] = public.get("status") or "OK"
            result["public_pages_read"] = total_pages_read
            result["public_inventory_complete"] = True
            result["fallback_reason"] = "NO_API_CREDENTIALS" if not creds else "API_FAILED"
            result["api_status"] = (api_failure or {}).get("status") if api_failure else ("NOT_CONFIGURED" if not creds else "OK")
            return result
        public_failure = public

    seller_rows = local_inventory_for_seller(alias, local_rows)
    combined_progress({
        "phase": "filter_start",
        "done": 0,
        "total": len(seller_rows),
        "found_count": len(seller_rows),
        "percent": 20,
    })
    result = _rank(
        alias,
        seller_rows,
        analyze_fn=analyze_fn,
        quick_limit=quick_limit,
        full_limit=full_limit,
        source="LOCAL_MARKET",
        progress_callback=progress_callback,
        ui=ui,
    )
    result = dict(result)
    result["local_market_count"] = len(local_rows)
    result["local_seller_match_count"] = len(seller_rows)
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
