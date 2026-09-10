"""Diversify which already-filtered listings receive full analysis.

This is a coverage mechanism only. It never changes valuation, ranking scores,
buy thresholds, max prices or decisions.
"""
from __future__ import annotations
from statistics import median


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _player_key(fast, idx):
    name = str((fast or {}).get("player_name") or "").strip().casefold()
    return name if name else f"__unknown_{idx}"


def _coverage_tags(item, fast, attention, price_median, demand_median):
    fast = fast or {}
    attention = attention or {}
    tags = []

    if fast.get("rookie_importance_matched") or fast.get("mispriced_rookie_candidate"):
        tags.append("rookie/prospect")

    if (
        _num(fast.get("variant_hierarchy_variant_rung")) > 0
        or _num(fast.get("valuable_card_structure_score")) > 0
        or bool(fast.get("valuable_card_tags"))
    ):
        tags.append("scarce/variant")

    if (
        fast.get("is_hidden_find_candidate")
        or fast.get("misclassified_card_candidate")
        or fast.get("is_information_edge_candidate")
    ):
        tags.append("underdescribed/research")

    demand_score = _num(fast.get("player_card_demand_score"))
    price = _num((item or {}).get("pris"), -1)
    if price >= 0 and price_median is not None and demand_score > 0:
        if price <= price_median and demand_score >= demand_median:
            tags.append("low-price+demand")

    if _num((attention or {}).get("score")) > 0:
        tags.append("market-attention")

    return tags


def diversify_full_analysis_indices(
    candidates,
    selected_indices,
    *,
    base_limit=12,
    hard_cap=30,
    coverage_slots=6,
    max_per_player=3,
):
    """Reserve tail slots for distinct evidence profiles.

    The baseline top-N is never removed. Existing adaptive selections after the
    baseline may be replaced only in the tail so several different candidate
    profiles get a chance at the same existing full analysis.
    """
    total = len(candidates or [])
    if total <= 0:
        return []

    base_limit = max(1, int(base_limit or 1))
    hard_cap = max(base_limit, int(hard_cap or base_limit))
    coverage_slots = max(0, min(int(coverage_slots or 0), hard_cap - base_limit))
    max_per_player = max(1, int(max_per_player or 1))

    selected = []
    seen = set()
    for raw in selected_indices or []:
        idx = int(raw)
        if 0 <= idx < total and idx not in seen:
            selected.append(idx)
            seen.add(idx)

    # Always preserve baseline indices even if a caller supplied a partial list.
    for idx in range(min(base_limit, total)):
        if idx not in seen:
            selected.insert(idx, idx)
            seen.add(idx)

    # Candidate-relative medians make coverage relative to the current search
    # instead of inventing a universal price/demand threshold.
    prices = [_num(item.get("pris"), -1) for item, _fast, _att in candidates]
    prices = [p for p in prices if p >= 0]
    price_median = median(prices) if prices else None
    demands = [_num((fast or {}).get("player_card_demand_score")) for _item, fast, _att in candidates]
    positive_demands = [d for d in demands if d > 0]
    demand_median = median(positive_demands) if positive_demands else 0.0

    baseline = list(range(min(base_limit, total)))
    adaptive_tail = [idx for idx in selected if idx not in baseline]

    # Keep room for coverage even when adaptive selection already filled cap.
    keep_adaptive = max(0, hard_cap - len(baseline) - coverage_slots)
    final = baseline + adaptive_tail[:keep_adaptive]
    final_seen = set(final)

    player_counts = {}
    for idx in final:
        _item, fast, _att = candidates[idx]
        key = _player_key(fast, idx)
        player_counts[key] = player_counts.get(key, 0) + 1

    pool = []
    for idx, (item, fast, attention) in enumerate(candidates):
        if idx in final_seen:
            continue
        tags = _coverage_tags(item, fast, attention, price_median, demand_median)
        if not tags:
            continue
        pool.append((
            -len(tags),
            -_num((fast or {}).get("rank_score")),
            idx,
            tags,
        ))
    pool.sort()

    added = 0
    covered_tags = set()
    while pool and len(final) < hard_cap and added < coverage_slots:
        # Prefer a row that adds a new coverage profile; otherwise take the
        # strongest remaining evidence-profile candidate.
        chosen_pos = None
        for pos, (_neg_tag_count, _neg_rank, idx, tags) in enumerate(pool):
            _item, fast, _attention = candidates[idx]
            key = _player_key(fast, idx)
            if player_counts.get(key, 0) >= max_per_player:
                continue
            if any(tag not in covered_tags for tag in tags):
                chosen_pos = pos
                break
        if chosen_pos is None:
            for pos, (_neg_tag_count, _neg_rank, idx, tags) in enumerate(pool):
                _item, fast, _attention = candidates[idx]
                key = _player_key(fast, idx)
                if player_counts.get(key, 0) < max_per_player:
                    chosen_pos = pos
                    break
        if chosen_pos is None:
            break

        _neg_tag_count, _neg_rank, idx, tags = pool.pop(chosen_pos)
        final.append(idx)
        final_seen.add(idx)
        _item, fast, _attention = candidates[idx]
        key = _player_key(fast, idx)
        player_counts[key] = player_counts.get(key, 0) + 1
        covered_tags.update(tags)
        added += 1

    # If coverage could not fill its reservation, put back strongest adaptive
    # selections before leaving capacity unused.
    for idx in adaptive_tail[keep_adaptive:]:
        if len(final) >= hard_cap:
            break
        if idx not in final_seen:
            final.append(idx)
            final_seen.add(idx)

    return final[:hard_cap]
