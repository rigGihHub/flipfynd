"""Compatibility layer for Tradera fetcher helpers.

Streamlit Cloud may briefly run a mixed deployment while files are being
replaced. Importing a newly added helper directly from ``src.tradera_fetcher``
can then crash the entire app. This module resolves helpers defensively so the
UI can still boot and show a degraded-but-safe state until all files match.
"""
from types import SimpleNamespace

DEFAULT_CATEGORY_URLS = {
    "Hockey - NHL": "https://www.tradera.com/category/293316",
    "Fotboll": "https://www.tradera.com/category/293311",
}


def _format_loaded_pages_fallback(pages):
    values = sorted({int(p) for p in (pages or []) if str(p).isdigit()})
    if not values:
        return "inga"
    ranges = []
    start = previous = values[0]
    for page in values[1:]:
        if page == previous + 1:
            previous = page
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = page
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return ", ".join(ranges)


def _load_fetch_state_fallback():
    return {"categories": {}}


def _prune_active_items_fallback(items, max_per_category=1500):
    return list(items or [])[: max(1, int(max_per_category or 1500)) * 2]


def _market_sync_fallback(category_name):
    return {
        "loaded_pages": [],
        "max_page_loaded": 0,
        "next_page": 1,
        "complete": False,
        "completed_at": None,
        "last_batch_start": None,
        "last_batch_end": None,
    }


def _market_coverage_fallback(category_name, now=None):
    return {
        **_market_sync_fallback(category_name),
        "loaded_page_count": 0,
        "contiguous_to": 0,
        "missing_pages": [],
        "coverage_label": "Marknadstäckning kan inte läsas i denna körning",
        "coverage_percent": None,
        "last_updated_at": None,
        "age_hours": None,
        "freshness": "unknown",
        "freshness_label": "Ingen färskhetsdata",
    }


def _smart_refresh_fallback(category_name, now=None, max_pages=8):
    return {
        "due": True,
        "start_page": 1,
        "end_page": min(max(1, int(max_pages or 8)), 5),
        "reason": "Smart refresh använder kompatibilitetsläge tills fetcher-versionen är synkad",
        "tier": "nyaste",
        "due_pages": [],
    }


def _noop(*args, **kwargs):
    return None


def _empty_list(*args, **kwargs):
    return []


def build_fetcher_api(module):
    """Resolve the fetcher API without hard failing on one missing new helper."""
    return SimpleNamespace(
        CATEGORY_URLS=getattr(module, "CATEGORY_URLS", DEFAULT_CATEGORY_URLS),
        clear_all_loaded_data=getattr(module, "clear_all_loaded_data", _noop),
        format_loaded_pages=getattr(module, "format_loaded_pages", _format_loaded_pages_fallback),
        load_fetch_state=getattr(module, "load_fetch_state", _load_fetch_state_fallback),
        prune_active_items=getattr(module, "prune_active_items", _prune_active_items_fallback),
        reconcile_market_state_with_items=getattr(module, "reconcile_market_state_with_items", _empty_list),
        SMART_MAX_PAGES=getattr(module, "SMART_MAX_PAGES", 12),
        MAX_ACTIVE_ITEMS_PER_CATEGORY=getattr(module, "MAX_ACTIVE_ITEMS_PER_CATEGORY", 1500),
        MARKET_BATCH_PAGES=getattr(module, "MARKET_BATCH_PAGES", 12),
        get_market_sync_status=getattr(module, "get_market_sync_status", _market_sync_fallback),
        get_market_coverage_status=getattr(module, "get_market_coverage_status", _market_coverage_fallback),
        get_smart_refresh_plan=getattr(module, "get_smart_refresh_plan", _smart_refresh_fallback),
        reset_market_sync=getattr(module, "reset_market_sync", _noop),
    )
