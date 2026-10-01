"""Persistent per-listing analysis coverage for Seller Top 5.

The registry travels with the existing seller checkpoint through session
state, local fallback storage and Postgres. It records coverage only; it never
changes valuation or BUY thresholds.
"""
from __future__ import annotations

from copy import deepcopy


SCHEMA = "seller-analysis-registry-v1"
BEST_ROW_LIMIT = 50


def listing_key(item: dict | None) -> str:
    item = item or {}
    for key in ("tradera_item_id", "item_id", "id", "lank", "url", "link"):
        value = item.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return str(item.get("titel") or item.get("title") or "").strip().casefold()


def normalize_registry(value: dict | None) -> dict:
    value = value if isinstance(value, dict) and value.get("schema") == SCHEMA else {}
    entries = value.get("entries") if isinstance(value.get("entries"), dict) else {}
    pending_rows = value.get("pending_rows") if isinstance(value.get("pending_rows"), dict) else {}
    best_rows = value.get("best_rows") if isinstance(value.get("best_rows"), dict) else {}
    clean_entries = {}
    for key, raw in entries.items():
        if not str(key).strip() or not isinstance(raw, dict):
            continue
        clean_entries[str(key)] = {
            "quick_count": max(0, int(raw.get("quick_count") or 0)),
            "full_count": max(0, int(raw.get("full_count") or 0)),
            "last_quick_run": max(0, int(raw.get("last_quick_run") or 0)),
            "last_full_run": max(0, int(raw.get("last_full_run") or 0)),
        }
    return {
        "schema": SCHEMA,
        "run": max(0, int(value.get("run") or 0)),
        "entries": clean_entries,
        "displayed_keys": [str(key) for key in value.get("displayed_keys", [])
                           if isinstance(key, (str, int))][:5],
        "pending_rows": {str(key): deepcopy(row) for key, row in pending_rows.items()
                         if str(key).strip() and isinstance(row, dict)},
        "best_rows": {
            str(key): deepcopy(row)
            for key, row in best_rows.items()
            if str(key).strip() and isinstance(row, dict)
        },
    }


def begin_run(value: dict | None) -> dict:
    registry = normalize_registry(value)
    registry["run"] += 1
    return registry


def analysis_count(registry: dict | None, item: dict | None, stage: str) -> int:
    registry = normalize_registry(registry)
    entry = registry["entries"].get(listing_key(item), {})
    return max(0, int(entry.get(f"{stage}_count") or 0))


def registry_progress(registry: dict | None) -> tuple[int, int, int]:
    """Monotonic coverage used when stale state layers disagree."""
    registry = normalize_registry(registry)
    entries = registry["entries"].values()
    full = sum(1 for entry in entries if int(entry.get("full_count") or 0) > 0)
    quick = sum(1 for entry in registry["entries"].values() if int(entry.get("quick_count") or 0) > 0)
    return full, quick, max(0, int(registry.get("run") or 0))


def record(registry: dict, items, stage: str) -> dict:
    if stage not in {"quick", "full"}:
        raise ValueError("stage must be quick or full")
    registry = normalize_registry(registry)
    run = max(1, int(registry.get("run") or 1))
    for item in items or []:
        key = listing_key(item)
        if not key:
            continue
        entry = registry["entries"].setdefault(key, {
            "quick_count": 0, "full_count": 0,
            "last_quick_run": 0, "last_full_run": 0,
        })
        entry[f"{stage}_count"] = max(0, int(entry.get(f"{stage}_count") or 0)) + 1
        entry[f"last_{stage}_run"] = run
    return registry


def rotate_unseen_first(items, registry: dict | None, *, stage: str) -> list[dict]:
    """Put never-analysed listings first and least-recently analysed next."""
    registry = normalize_registry(registry)
    entries = registry["entries"]
    indexed = list(enumerate(item for item in (items or []) if isinstance(item, dict)))

    def key(pair):
        position, item = pair
        entry = entries.get(listing_key(item.get("source_item") or item), {})
        count = max(0, int(entry.get(f"{stage}_count") or 0))
        last_run = max(0, int(entry.get(f"last_{stage}_run") or 0))
        return (count > 0, count, last_run, position)

    return [item for _position, item in sorted(indexed, key=key)]


def coverage(registry: dict | None, inventory) -> dict:
    registry = normalize_registry(registry)
    keys = {listing_key(item) for item in (inventory or []) if listing_key(item)}
    entries = registry["entries"]
    quick = sum(1 for key in keys if int((entries.get(key) or {}).get("quick_count") or 0) > 0)
    full = sum(1 for key in keys if int((entries.get(key) or {}).get("full_count") or 0) > 0)
    total = len(keys)
    return {
        "inventory_unique": total,
        "quick_unique": quick,
        "quick_remaining": max(0, total - quick),
        "full_unique": full,
        "full_remaining": max(0, total - full),
        "full_complete": total > 0 and full >= total,
    }


def merge_best_rows(registry: dict, rows, *, rank_key, presentable) -> tuple[dict, list[dict]]:
    registry = normalize_registry(registry)
    merged = {key: row for key, row in (registry.get("best_rows") or {}).items()
              if presentable(row)}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        key = listing_key(row.get("source_item") or row)
        if key:
            if presentable(row):
                merged[key] = deepcopy(row)
            else:
                # A current loss/invalid result supersedes its old highlight.
                merged.pop(key, None)
    ordered = sorted(merged.values(), key=rank_key, reverse=True)[:BEST_ROW_LIMIT]
    registry["best_rows"] = {
        listing_key(row.get("source_item") or row): deepcopy(row)
        for row in ordered
        if listing_key(row.get("source_item") or row)
    }
    return registry, ordered


__all__ = [
    "SCHEMA", "analysis_count", "begin_run", "coverage", "listing_key",
    "merge_best_rows", "normalize_registry", "record", "registry_progress",
    "rotate_unseen_first",
]
