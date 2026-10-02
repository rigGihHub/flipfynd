"""Keep a cumulative comparison list without changing the BUY evidence gate."""
from copy import deepcopy
from math import isfinite

from src.seller_analysis_registry import BEST_ROW_LIMIT, listing_key, normalize_registry
from src.seller_card_domain import seller_item_domain_check


def alternative_listing_key(row):
    return str(row.get("seller_listing_key") or listing_key(row.get("source_item") or row))


def displayable_alternative(row):
    if not isinstance(row, dict):
        return False
    source = row.get('source_item') or row
    if not listing_key(source) or not (row.get('title') or source.get('titel') or source.get('title')):
        return False
    if not seller_item_domain_check(source, sport='all').get('allowed'):
        return False
    containers = (row,) if any(k in row for k in ('price', 'pris', 'current_price')) else (source,)
    for container in containers:
        for key in ('price', 'pris', 'current_price'):
            value = container.get(key)
            if value in (None, '') or isinstance(value, bool):
                continue
            try:
                price = float(value)
                return isfinite(price) and price > 0
            except (TypeError, ValueError):
                continue
    return False



def merge_dismissed(registry, *others):
    registry = normalize_registry(registry)
    hidden = set(registry['dismissed_keys'])
    for other in others:
        hidden.update(normalize_registry(other)['dismissed_keys'])
    registry['dismissed_keys'] = sorted(hidden)
    return registry


def select_saved_top5(registry, *, rank_key, select_diverse):
    registry = normalize_registry(registry)
    hidden = set(registry['dismissed_keys'])
    ordered = sorted((row for row in registry['alternative_rows'].values()
                      if alternative_listing_key(row) not in hidden and displayable_alternative(row)),
                     key=rank_key, reverse=True)
    selected, _, _ = select_diverse(ordered, 5)
    if len(selected) < 5:
        used = {alternative_listing_key(row) for row in selected}
        selected += [row for row in ordered if alternative_listing_key(row) not in used][:5-len(selected)]
    return [dict(row, seller_top5_alternative=True) for row in selected]


def dismiss_seller_alternative(result, key):
    """Remove one listing and promote the next saved candidate, without fetching."""
    # Late imports avoid a cycle with the builder's dynamic-list integration.
    from src.seller_top5 import _seller_alternative_rank_key, _select_diverse_rows
    result = deepcopy(result or {})
    checkpoint = result.get('public_checkpoint') or {}
    registry = merge_dismissed(result.get('analysis_registry'), checkpoint.get('analysis_registry'))
    for row in result.get('alternatives', result.get('rows') or []):
        registry['alternative_rows'].setdefault(alternative_listing_key(row), deepcopy(row))
    available = set(registry['alternative_rows'])
    if str(key) not in available:
        return result
    registry['dismissed_keys'] = sorted(set(registry['dismissed_keys']) | {str(key)})
    alternatives = select_saved_top5(registry, rank_key=_seller_alternative_rank_key,
                                     select_diverse=_select_diverse_rows)
    previous = set(registry['displayed_keys'])
    registry['displayed_keys'] = [alternative_listing_key(row) for row in alternatives]
    result['alternatives'] = alternatives
    result['analysis_registry'] = registry
    result['top5_new_count'] = len(set(registry['displayed_keys']) - previous)
    result['dismissed_count'] = len(registry['dismissed_keys'])
    if checkpoint:
        result['public_checkpoint']['analysis_registry'] = deepcopy(registry)
    return result

def update_dynamic_top5(registry, *, inventory, quick_rows, full_rows, seed_rows,
                        rank_key, refresh, quick_fallback, select_diverse):
    """Full results replace fast results; new rounds compete with retained rows."""
    registry = normalize_registry(registry)
    hidden = set(registry['dismissed_keys'])
    keys = {listing_key(item) for item in inventory} - hidden
    retained = dict(registry.get('alternative_rows') or {})
    for row in seed_rows:
        retained.setdefault(alternative_listing_key(row), row)
    retained = {key: refresh(row) for key, row in retained.items()
                if key in keys and displayable_alternative(row)}
    for quick in quick_rows:
        source = quick.get('source_item') or quick
        key = listing_key(source)
        if key in hidden:
            continue
        if (registry['entries'].get(key) or {}).get('full_count'):
            continue
        if (retained.get(key) or {}).get('analysis_level') == 'full':
            continue
        row = refresh(quick_fallback(quick))
        if displayable_alternative(row):
            retained[key] = row
    for row in full_rows:
        key = alternative_listing_key(row)
        if key in hidden:
            continue
        if displayable_alternative(row):
            retained[key] = refresh(row)
        else:
            retained.pop(key, None)
    ordered = sorted(retained.values(), key=rank_key, reverse=True)
    # Store distinct opportunities first so duplicate listings do not crowd
    # better alternatives out of the bounded checkpoint.
    distinct, _, _ = select_diverse(ordered, BEST_ROW_LIMIT)
    distinct_keys = {alternative_listing_key(row) for row in distinct}
    saved = (distinct + [row for row in ordered
                         if alternative_listing_key(row) not in distinct_keys])[:BEST_ROW_LIMIT]
    registry['alternative_rows'] = {alternative_listing_key(row): deepcopy(row) for row in saved}
    selected = select_saved_top5(registry, rank_key=rank_key, select_diverse=select_diverse)
    return registry, selected
