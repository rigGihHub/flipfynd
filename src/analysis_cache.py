import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from threading import RLock
from src.snapshot_encoding import json_size

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_PATH = BASE_DIR / "analysis_cache.json"

CACHE_SCHEMA_VERSION = 2
CACHE_MODEL_VERSION = "flip_v39_evidence_first_collector_review"
CACHE_MAX_ENTRIES = 128
CACHE_MAX_BYTES = 8 * 1024 * 1024
_LOCK = RLock()

_memory_cache: Optional[Dict[str, Any]] = None


def _now_ts() -> float:
    return time.time()


def _empty_cache_payload() -> dict:
    return {
        "_meta": {
            "schema_version": CACHE_SCHEMA_VERSION,
            "model_version": CACHE_MODEL_VERSION,
            "updated_at": _now_ts(),
        },
        "entries": {},
    }


def _is_valid_cache_payload(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if "_meta" not in data or "entries" not in data:
        return False
    if not isinstance(data.get("_meta"), dict):
        return False
    if not isinstance(data.get("entries"), dict):
        return False
    return True


def _normalize_loaded_payload(data: Any) -> dict:
    if not _is_valid_cache_payload(data):
        return _empty_cache_payload()

    meta = data.get("_meta", {})
    entries = data.get("entries", {})

    schema_version = meta.get("schema_version")
    model_version = meta.get("model_version")

    if schema_version != CACHE_SCHEMA_VERSION or model_version != CACHE_MODEL_VERSION:
        return _empty_cache_payload()

    normalized = {
        "_meta": {
            "schema_version": CACHE_SCHEMA_VERSION,
            "model_version": CACHE_MODEL_VERSION,
            "updated_at": meta.get("updated_at", _now_ts()),
        },
        "entries": {},
    }

    for key, value in sorted(entries.items(), key=lambda pair:
            (pair[1].get('last_accessed', 0), pair[1].get('created_at', 0))
            if isinstance(pair[1], dict) else (0, 0), reverse=True)[:CACHE_MAX_ENTRIES]:
        if not isinstance(key, str):
            continue
        if not isinstance(value, dict):
            continue
        if "result" not in value:
            continue

        normalized["entries"][key] = {
            "result": value.get("result"),
            "created_at": value.get("created_at", _now_ts()),
            "last_accessed": value.get("last_accessed", _now_ts()),
            "size_bytes": json_size(value.get('result'), CACHE_MAX_BYTES),
        }
    normalized['entries'] = _prune_entries(normalized['entries'])
    return normalized


def _load_cache_payload() -> dict:
    global _memory_cache

    if _memory_cache is not None:
        return _memory_cache

    if not CACHE_PATH.exists():
        _memory_cache = _empty_cache_payload()
        return _memory_cache

    # This is a recomputable analysis cache, separate from saved searches.
    # Do not deserialize an old oversized cache before its new bound applies.
    try:
        if CACHE_PATH.stat().st_size > CACHE_MAX_BYTES * 2:
            _memory_cache = _empty_cache_payload()
            return _memory_cache
        with CACHE_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        _memory_cache = _empty_cache_payload()
        return _memory_cache

    _memory_cache = _normalize_loaded_payload(data)
    return _memory_cache


def _save_cache_payload(payload: dict) -> None:
    global _memory_cache

    payload["_meta"]["updated_at"] = _now_ts()
    _memory_cache = payload

    try:
        with CACHE_PATH.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _prune_entries(entries: dict, max_entries: int = CACHE_MAX_ENTRIES) -> dict:
    pruned, used = {}, 0
    for key, entry in sorted(entries.items(), key=lambda pair:
            (pair[1].get('last_accessed', 0), pair[1].get('created_at', 0)), reverse=True):
        size = entry.get('size_bytes')
        if size is None:
            size = json_size(entry.get('result'), CACHE_MAX_BYTES)
            entry['size_bytes'] = size
        if len(pruned) < max_entries and used + size <= CACHE_MAX_BYTES:
            pruned[key] = entry
            used += size
    return pruned


def clear_analysis_cache() -> None:
    global _memory_cache
    _memory_cache = None

    if CACHE_PATH.exists():
        try:
            CACHE_PATH.unlink()
        except Exception:
            pass


def build_analysis_signature(item: dict, data_size: int, mode: str) -> str:
    payload = {
        "cache_model_version": CACHE_MODEL_VERSION,
        "lank": item.get("lank", ""),
        "titel": item.get("titel", ""),
        "pris": item.get("pris"),
        "frakt": item.get("frakt"),
        "raw_text": item.get("raw_text", ""),
        "full_description": item.get("full_description", ""),
        "purchase_detail_verified": item.get("purchase_detail_verified", False),
        "listing_inactive": item.get("listing_inactive", False),
        "data_size": data_size,
        "mode": mode,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached_analysis(signature: str):
    with _LOCK:
        return _get_cached_analysis(signature)


def _get_cached_analysis(signature: str):
    payload = _load_cache_payload()
    entries = payload["entries"]

    entry = entries.get(signature)
    if not entry:
        return None

    result = entry.get("result")
    if str(((result or {}).get("asking_price_opportunity") or {}).get("status", "")).startswith("COMPARISON_"):
        return None
    context = (result or {}).get("ebay_active_context")
    if context:
        try:
            fetched_at = datetime.fromisoformat(context["fetched_at"])
            age = (datetime.now(timezone.utc) - fetched_at).total_seconds()
            if not 0 <= age < 900:
                return None
        except (KeyError, ValueError, TypeError):
            return None
    entry["last_accessed"] = _now_ts()
    return result


def set_cached_analysis(signature: str, result: dict) -> None:
    with _LOCK:
        _set_cached_analysis(signature, result)


def _set_cached_analysis(signature: str, result: dict) -> None:
    if str((result.get("asking_price_opportunity") or {}).get("status", "")).startswith("COMPARISON_"):
        return
    try:
        size = json_size(result, CACHE_MAX_BYTES)
    except (TypeError, ValueError):
        return  # An optional cache must never fail an otherwise valid analysis.
    payload = _load_cache_payload()
    entries = payload["entries"]

    existing = entries.get(signature)
    created_at = existing.get("created_at", _now_ts()) if isinstance(existing, dict) else _now_ts()

    entries[signature] = {
        "result": result,
        "created_at": created_at,
        "last_accessed": _now_ts(),
        "size_bytes": size,
    }

    payload["entries"] = _prune_entries(entries, max_entries=CACHE_MAX_ENTRIES)
    _save_cache_payload(payload)
