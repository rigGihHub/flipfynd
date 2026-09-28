"""Reserve bounded fast-analysis capacity for price-researchable listings."""
from __future__ import annotations


def _key(row):
    for field in ("tradera_item_id", "id", "item_id", "lank", "url", "link"):
        value = (row or {}).get(field)
        if value not in (None, ""):
            return str(value).strip()
    return "|".join(str((row or {}).get(field) or "").strip().casefold()
                    for field in ("titel", "title", "pris", "frakt"))


def add_price_route_coverage(selected, ordered_routes, *, max_new=40):
    """Replace low-priority nonroutes, retaining the pool size and first quarter.

    Routes are prevalidated by the existing exact-identity/price selector.
    This only changes which listings receive analysis; it creates no price,
    comparison, profit, or purchase recommendation.
    """
    selected = list(selected or [])
    if not selected or not ordered_routes or max_new <= 0:
        return selected, 0
    route_keys = {_key(row) for row in ordered_routes}
    selected_keys = {_key(row) for row in selected}
    protected = max(1, len(selected) // 4)
    replaceable = [index for index in range(len(selected) - 1, protected - 1, -1)
                   if _key(selected[index]) not in route_keys]
    added = 0
    for route in ordered_routes:
        key = _key(route)
        if key in selected_keys or not replaceable or added >= max_new:
            continue
        index = replaceable.pop(0)
        selected_keys.discard(_key(selected[index]))
        selected[index] = route
        selected_keys.add(key)
        added += 1
    return selected, added
