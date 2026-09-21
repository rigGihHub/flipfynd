"""Choose the safest available inventory source for Seller Top 5.

One click owns the whole seller workflow. Public Tradera profiles are read in
small checkpointed batches so Streamlit never needs to keep one very long
request alive. Partial inventories may show a provisional Top 5; completed
inventories get the final ranking.
"""
from __future__ import annotations

from typing import Callable, Iterable
from urllib.parse import quote

from src.seller_checkpoint_store import clear_checkpoint, load_checkpoint, save_checkpoint
from src.public_seller_inventory import fetch_public_seller_inventory_batch, parse_profile_url
from src.seller_proxy_inventory import fetch_proxy_seller_inventory_batch
from src.seller_top5 import build_seller_top5
from src.seller_card_domain import seller_item_domain_check
from src.seller_top5_fallback import local_inventory_for_seller
from src.tradera_seller_inventory import discover_active_seller_inventory

PUBLIC_BATCH_PAGES = 9
_CHECKPOINT_SCHEMA = "v3"


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
    """Compatibility shim. Seller Top 5 renders progress only in app.py."""
    def __init__(self, enabled: bool = True):
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

    rows = [dict(x) for x in (items or []) if isinstance(x, dict)]
    result = build_seller_top5(
        alias,
        rows,
        analyze_fn=analyze_fn,
        sport="all",
        quick_limit=quick_limit,
        full_limit=full_limit,
        progress_callback=combined_progress,
    )
    result = dict(result)
    result["inventory_source"] = source
    return result


def _fetch_public(public_fetcher, profile_url, *, start_page, public_pages, progress_callback=None, seller_alias=None, paging_size=None):
    kwargs = {
        "start_page": max(1, int(start_page or 1)),
        "max_pages": max(1, int(public_pages or 1)),
    }
    if progress_callback is not None:
        kwargs["progress_callback"] = progress_callback
    if str(seller_alias or "").strip():
        kwargs["fallback_alias"] = str(seller_alias).strip()
    if paging_size:
        kwargs["paging_size"] = int(paging_size)

    for optional_key in ("paging_size", "fallback_alias", "progress_callback"):
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
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is not None:
            return st.session_state
    except Exception:
        pass
    return None


def _checkpoint_key(alias: str, profile_url: str) -> str:
    # Schema suffix intentionally invalidates checkpoints created by older
    # versions that could accidentally contain the full local market.
    return (
        "seller_public_checkpoint::"
        + _CHECKPOINT_SCHEMA
        + "::"
        + str(alias or "").strip().casefold()
        + "::"
        + str(profile_url or "").strip()
    )


def reset_seller_top5_search(seller: str, profile_url: str, *, database_url=None, session=None) -> str:
    """Clear every continuation layer for one public seller search."""
    profile_text = str(profile_url or "").strip()
    parsed = parse_profile_url(profile_text) or {}
    alias = str(seller or parsed.get("alias") or "").strip()
    if not alias and parsed.get("seller_id"):
        alias = f"Tradera #{parsed.get('seller_id')}"
    if session is None:
        session = _streamlit_session_state()

    # app.py adds the seller alias to numeric Tradera profile URLs before a
    # crawl. The form retains the original URL, so reset must clear both forms.
    profile_variants = [profile_text]
    stripped = profile_text.rstrip("/")
    if stripped and stripped != profile_text:
        profile_variants.append(stripped)
    base, separator, query = stripped.partition("?")
    clean_base = base.rstrip("/")
    if alias and "/profile/items/" in clean_base and clean_base.rsplit("/", 1)[-1].isdigit():
        canonical = clean_base + "/" + quote(alias, safe="")
        if separator:
            canonical += "?" + query
        profile_variants.append(canonical)

    cleared_keys = []
    for candidate in dict.fromkeys(profile_variants):
        key = _checkpoint_key(alias, candidate)
        clear_checkpoint(key, session=session, database_url=database_url)
        cleared_keys.append(key)
    return cleared_keys[-1]


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


def _public_item_matches_profile(item: dict, *, seller_alias: str, seller_id: str | None) -> bool:
    if not isinstance(item, dict):
        return False
    if str(item.get("source_type") or "") != "tradera_public_seller_profile":
        return False
    item_seller_id = str(item.get("seller_user_id") or "").strip()
    if seller_id and item_seller_id and item_seller_id != str(seller_id):
        return False
    item_alias = str(item.get("saljare") or item.get("seller") or item.get("seller_name") or "").strip()
    if seller_alias and item_alias and item_alias.casefold() != seller_alias.casefold():
        return False
    return bool(_item_key(item))


def _sanitize_public_items(items, *, seller_alias: str, seller_id: str | None) -> dict[str, dict]:
    clean: dict[str, dict] = {}
    for item in items or []:
        if _public_item_matches_profile(item, seller_alias=seller_alias, seller_id=seller_id):
            clean[_item_key(item)] = dict(item)
    return clean


def _partial_result_from_saved(
    alias: str,
    saved_items: dict[str, dict],
    *,
    analyze_fn: Callable,
    quick_limit: int,
    full_limit: int,
    progress_callback,
    ui,
    public_status: str,
    public_error,
    pages_read: int,
    next_page: int,
    api_status: str,
    fallback_reason: str,
    resume_required: bool,
    total_listing_estimate: int | None = None,
):
    """Rank every saved page with the ordinary FlipFynd Seller Top 5 engine.

    A partial profile is provisional because more listings remain, not because
    it uses weaker ranking. One Tradera page is small enough for the regular
    quick scan plus the bounded deep-analysis shortlist.
    """
    ranked = _rank(
        alias,
        saved_items.values(),
        analyze_fn=analyze_fn,
        quick_limit=quick_limit,
        full_limit=full_limit,
        source="TRADERA_PUBLIC_PROFILE",
        progress_callback=progress_callback,
        ui=ui,
    )
    rows = list(ranked.get("rows") or [])[:5]
    loaded = len(saved_items)
    remaining = max(0, int(total_listing_estimate) - loaded) if total_listing_estimate else None
    result = dict(ranked)
    result.update({
        "seller": alias,
        "diagnostic_code": (
            str(public_error.get("diagnostic_code"))
            if isinstance(public_error, dict) and public_error.get("diagnostic_code")
            else "FF-SELLER-BATCH-COMPLETE"
            if public_status == "OK" and loaded > 0 and resume_required is False
            else "FF-SELLER-FETCH-INTERRUPTED" if resume_required else "FF-SELLER-PARTIAL"
        ),
        "rows": rows,
        "status": "INVENTORY_PARTIAL",
        "inventory_count": loaded,
        "inventory_source": "TRADERA_PUBLIC_PROFILE",
        "public_status": public_status,
        "public_error": public_error,
        "public_pages_read": pages_read,
        "public_next_page": next_page,
        "public_batch_pages": 0,
        "public_inventory_complete": False,
        "provisional_top5": bool(rows),
        "resume_required": bool(resume_required),
        "fallback_reason": fallback_reason,
        "api_status": api_status,
        "total_listing_estimate": total_listing_estimate,
        "remaining_listing_estimate": remaining,
        # Mirror the continuation state in the visible result. Streamlit keeps
        # this object reliably between button clicks even when an auxiliary
        # checkpoint backend is unavailable.
        "public_checkpoint": {
            "next_page": next_page,
            "pages_read": pages_read,
            "items": dict(saved_items),
            "total_listing_estimate": total_listing_estimate,
        },
    })
    return result


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
    database_url=None,
    resume_checkpoint=None,
) -> dict:
    alias = str(seller or "").strip()
    profile_text = str(profile_url or "").strip()
    input_profile = parse_profile_url(profile_text) or {}
    if not alias:
        alias = str(input_profile.get("alias") or "").strip()
    if not alias and input_profile.get("seller_id"):
        alias = f"Tradera #{input_profile.get('seller_id')}"
    local_rows = [dict(x) for x in (market_items or []) if isinstance(x, dict)]
    if not alias:
        return {"status": "NO_SELLER", "rows": [], "seller": None,
                "inventory_count": 0, "inventory_source": "NONE", "fallback_reason": None}

    ui = _SellerProgress(enabled=False)

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

    if profile_text:
        session = _streamlit_session_state()
        parsed_profile = parse_profile_url(profile_text) or {}
        seller_id = str(parsed_profile.get("seller_id") or "").strip() or None
        key = _checkpoint_key(alias, profile_text)
        # Durable/local/session state and the visible result can temporarily
        # disagree after a rerun. Always choose the furthest checkpoint; never
        # let an older visible result rewind a crawl already persisted.
        durable_checkpoint = load_checkpoint(key, session=session, database_url=database_url)
        from src.seller_checkpoint_store import furthest_checkpoint
        checkpoint = furthest_checkpoint(durable_checkpoint, resume_checkpoint)
        if not isinstance(checkpoint, dict):
            checkpoint = {"next_page": 1, "pages_read": 0, "items": {}, "total_listing_estimate": None}
        # pages_read must describe unique pages represented by the cursor, not
        # accumulate repeated blocks from stale checkpoints.
        checkpoint["pages_read"] = max(0, int(checkpoint.get("next_page") or 1) - 1)

        raw_checkpoint_items = (checkpoint.get("items") or {}).values() if isinstance(checkpoint.get("items"), dict) else []
        stored_items = _sanitize_public_items(raw_checkpoint_items, seller_alias=alias, seller_id=seller_id)
        if len(stored_items) != len(checkpoint.get("items") or {}):
            checkpoint = {
                "next_page": 1,
                "pages_read": 0,
                "items": {},
                "total_listing_estimate": None,
            }
            stored_items = {}
            save_checkpoint(key, checkpoint, session=session, database_url=database_url)

        start_page = max(1, int(checkpoint.get("next_page") or 1))
        print(
            f"SELLER_CONTROLLER_START alias={alias} start_page={start_page} "
            f"checkpoint_next={checkpoint.get('next_page')} items={len(stored_items)} "
            f"resume_supplied={isinstance(resume_checkpoint, dict)}",
            flush=True,
        )
        # Read several checkpointed pages per click. Each page is saved
        # immediately, so a timeout/session loss resumes from the next page.
        batch_pages = min(PUBLIC_BATCH_PAGES, max(1, int(public_pages or PUBLIC_BATCH_PAGES)))
        current_page = start_page
        pages_this_run = 0
        exhausted = False
        public_failure = None
        total_listing_estimate = checkpoint.get("total_listing_estimate")

        for _ in range(batch_pages):
            # For public seller continuation, the Render proxy is the
            # authoritative fetch path. Passing current_page through unchanged
            # guarantees page 10 stays page 10 instead of being rebuilt by the
            # legacy direct Tradera URL helper.
            try:
                page_result = fetch_proxy_seller_inventory_batch(
                    profile_text,
                    start_page=current_page,
                    max_pages=1,
                    progress_callback=combined_progress,
                    fallback_alias=alias,
                )
            except Exception as exc:
                page_result = {
                    "ok": False,
                    "status": "PROXY_FETCH_EXCEPTION",
                    "error": str(exc),
                    "items": [],
                    "next_page": current_page,
                }

            if not page_result.get("ok"):
                public_failure = page_result
                break

            resolved_alias = str(((page_result.get("seller") or {}).get("alias")) or "").strip()
            if resolved_alias:
                alias = resolved_alias

            if page_result.get("total_listing_estimate"):
                total_listing_estimate = int(page_result.get("total_listing_estimate"))
            page_items = _sanitize_public_items(
                page_result.get("items") or [], seller_alias=alias, seller_id=seller_id
            )
            new_item_keys = set(page_items) - set(stored_items)
            if current_page > 1 and page_items and not new_item_keys:
                # The proxy may legitimately return overlapping listings when
                # Tradera reorders a large seller inventory. Do not turn a
                # successful HTTP page into a fatal error. Advance the cursor;
                # later pages can still contribute new item ids. The bounded
                # block prevents an infinite loop.
                combined_progress({
                    "phase": "page_overlap",
                    "page": current_page,
                    "pages_read": pages_this_run,
                    "max_pages": batch_pages,
                    "found_count": len(stored_items),
                    "page_count": len(page_items),
                })
                public_failure = {
                    "status": "NO_NEW_IDS",
                    "error": f"Sida {current_page} gav 0 nya annons-ID:n.",
                    "navigation_links": page_result.get("navigation_links") or [],
                }
                # A fully overlapping page is not necessarily EOF: live
                # inventories can shift between requests. Count the page as
                # successfully represented and advance, while the bounded
                # batch prevents an infinite crawl.
                pages_this_run += int(page_result.get("pages_read") or 1)
                current_page = int(page_result.get("next_page") or (current_page + 1))
                checkpoint = {
                    "next_page": current_page,
                    "pages_read": max(0, current_page - 1),
                    "items": stored_items,
                    "total_listing_estimate": total_listing_estimate,
                }
                save_checkpoint(key, checkpoint, session=session, database_url=database_url)
                public_failure = None
                continue
            stored_items.update(page_items)
            pages_this_run += int(page_result.get("pages_read") or 0)
            current_page = int(page_result.get("next_page") or (current_page + 1))
            exhausted = bool(page_result.get("exhausted"))
            checkpoint = {
                "next_page": current_page,
                "pages_read": max(0, current_page - 1),
                "items": stored_items,
                "total_listing_estimate": total_listing_estimate,
            }
            save_checkpoint(
                key,
                checkpoint,
                session=session,
                database_url=database_url,
            )
            if exhausted:
                break

        total_pages_read = int(checkpoint.get("pages_read") or 0)
        api_status = (api_failure or {}).get("status") if api_failure else ("NOT_CONFIGURED" if not creds else "OK")

        if public_failure:
            return _partial_result_from_saved(
                alias,
                stored_items,
                analyze_fn=analyze_fn,
                quick_limit=quick_limit,
                full_limit=full_limit,
                progress_callback=progress_callback,
                ui=ui,
                public_status=public_failure.get("status") or "FETCH_FAILED",
                public_error=public_failure.get("error"),
                pages_read=total_pages_read,
                next_page=current_page,
                api_status=api_status,
                fallback_reason="PUBLIC_PROFILE_INTERRUPTED",
                resume_required=True,
                total_listing_estimate=total_listing_estimate,
            )

        if not exhausted:
            save_checkpoint(
                key,
                {"next_page": current_page, "pages_read": total_pages_read, "items": stored_items, "total_listing_estimate": total_listing_estimate},
                session=session,
                database_url=database_url,
            )
            return _partial_result_from_saved(
                alias,
                stored_items,
                analyze_fn=analyze_fn,
                quick_limit=quick_limit,
                full_limit=full_limit,
                progress_callback=progress_callback,
                ui=ui,
                public_status="OK",
                public_error=None,
                pages_read=total_pages_read,
                next_page=current_page,
                api_status=api_status,
                fallback_reason="NO_API_CREDENTIALS" if not creds else "API_FAILED",
                resume_required=False,
                total_listing_estimate=total_listing_estimate,
            )

        clear_checkpoint(key, session=session, database_url=database_url)
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
        result["public_status"] = "OK"
        result["public_pages_read"] = total_pages_read
        result["public_inventory_complete"] = True
        result["fallback_reason"] = "NO_API_CREDENTIALS" if not creds else "API_FAILED"
        result["api_status"] = api_status
        return result

    # Only use the local market when no public profile URL was supplied.
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
    return result
