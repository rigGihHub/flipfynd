"""Bounded network screening beyond the CPU analysis shortlist."""
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
import time

from src.analysis_scope import _listing_key
from src.search_progress import begin_phase, report_phase
from src.price_research_checkpoint import listing_fingerprint


def sweep_inventory(routes, analysed, enrich, *, workers=6, seconds=600, limit=1000, completed=()):
    """Screen unseen listings, retaining input order and stopping on API limits.

    No ranking/value rules live here. Only the existing exact comparison
    function may produce a research signal. Never runs full CPU analysis.
    """
    seen = {_listing_key(row) for row in analysed
            if isinstance(row.get("asking_price_opportunity"), dict)}
    pending = []
    completed = set(completed)
    previous_count = 0
    for route in routes:
        row = route.get("source_item") or route
        key = _listing_key(row)
        if listing_fingerprint(row) in completed:
            previous_count += 1
            continue
        if key not in seen:
            seen.add(key)
            pending.append(row)
    if any((row.get("asking_price_opportunity") or {}).get("http_status")
           in {401, 403, 429} for row in analysed):
        return [], {"inventory_price_checked": 0,
                    "inventory_price_remaining": len(pending),
                    "inventory_price_previously_checked": previous_count,
                    "inventory_price_stop": "API_LIMIT", "inventory_price_seconds": 0}
    results = []
    begin_phase("Prisjämför återstående kort", len(pending))
    started = time.monotonic()
    stop = "COMPLETE"
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for offset in range(0, min(len(pending), limit), workers):
            if time.monotonic() - started >= seconds:
                stop = "TIME_LIMIT"
                break
            batch = pending[offset:min(offset + workers, limit)]
            futures = [executor.submit(copy_context().run, enrich, row) for row in batch]
            results.extend(future.result() for future in futures)
            report_phase("Prisjämför återstående kort", checked=len(results), total=len(pending))
            if any((row.get("asking_price_opportunity") or {}).get("http_status")
                   in {401, 403, 429} for row in results[-len(batch):]):
                stop = "API_LIMIT"
                break
    remaining = len(pending) - len(results)
    if remaining and stop == "COMPLETE":
        stop = "REQUEST_LIMIT"
    return results, {"inventory_price_checked": len(results),
                     "inventory_price_previously_checked": previous_count,
                     "inventory_price_remaining": remaining,
                     "inventory_price_stop": stop,
                     "inventory_price_seconds": round(time.monotonic() - started, 2)}
