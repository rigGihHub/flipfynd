import hashlib
import json


SEARCH_RESULT_SCHEMA_VERSION = 1


def build_search_run_signature(
    *, data_version: str, app_version: str, sport: str, search: str,
    max_price: float, sale_type: str, strategy: str, numbered_only: bool,
    patch_only: bool, auto_only: bool,
) -> str:
    """Identify a completed search that is safe to reuse."""
    payload = {
        "schema": SEARCH_RESULT_SCHEMA_VERSION,
        "data_version": str(data_version or ""),
        "app_version": str(app_version or ""),
        "sport": str(sport or ""),
        "search": " ".join(str(search or "").casefold().split()),
        "max_price": round(float(max_price), 2),
        "sale_type": str(sale_type or ""),
        "strategy": str(strategy or ""),
        "numbered_only": bool(numbered_only),
        "patch_only": bool(patch_only),
        "auto_only": bool(auto_only),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_reusable_search(cache: dict | None, signature: str):
    entry = (cache or {}).get(signature)
    if not isinstance(entry, dict):
        return None
    results = entry.get("results")
    debug = entry.get("debug")
    if not isinstance(results, list) or not isinstance(debug, dict):
        return None
    return results, debug


def store_reusable_search(signature: str, results: list, debug: dict) -> dict:
    """Keep one completed run per session to bound memory usage."""
    return {signature: {"results": results, "debug": debug}}
