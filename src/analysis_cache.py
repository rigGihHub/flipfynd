import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_PATH = BASE_DIR / "analysis_cache.json"

CACHE_SCHEMA_VERSION = 2
CACHE_MODEL_VERSION = "flip_v26_exact_premium_valuation"

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

    for key, value in entries.items():
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
        }

    return normalized


def _load_cache_payload() -> dict:
    global _memory_cache

    if _memory_cache is not None:
        return _memory_cache

    if not CACHE_PATH.exists():
        _memory_cache = _empty_cache_payload()
        return _memory_cache

    try:
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


def _prune_entries(entries: dict, max_entries: int = 4000) -> dict:
    if len(entries) <= max_entries:
        return entries

    sortable = []
    for key, value in entries.items():
        last_accessed = value.get("last_accessed", 0)
        created_at = value.get("created_at", 0)
        sortable.append((key, last_accessed, created_at))

    sortable.sort(key=lambda x: (x[1], x[2]))  # äldst/sämst använda först

    remove_count = len(entries) - max_entries
    keys_to_remove = {row[0] for row in sortable[:remove_count]}

    pruned = {}
    for key, value in entries.items():
        if key not in keys_to_remove:
            pruned[key] = value

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
        "data_size": data_size,
        "mode": mode,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached_analysis(signature: str):
    payload = _load_cache_payload()
    entries = payload["entries"]

    entry = entries.get(signature)
    if not entry:
        return None

    entry["last_accessed"] = _now_ts()
    return entry.get("result")


def set_cached_analysis(signature: str, result: dict) -> None:
    payload = _load_cache_payload()
    entries = payload["entries"]

    existing = entries.get(signature)
    created_at = existing.get("created_at", _now_ts()) if isinstance(existing, dict) else _now_ts()

    entries[signature] = {
        "result": result,
        "created_at": created_at,
        "last_accessed": _now_ts(),
    }

    payload["entries"] = _prune_entries(entries, max_entries=4000)
    _save_cache_payload(payload)