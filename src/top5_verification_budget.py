"""Reserve deep-analysis slots for candidates likely to reach Top 5.

This is a routing layer only. It does not create value, SOLD evidence or BUY.
Its purpose is to spend the limited external/asking research budget on rows
that could otherwise rank highly on cheap discovery signals.
"""
from __future__ import annotations


def _n(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _priority(candidate, idx):
    item, fast, attention = candidate
    total = _n(fast.get("analysis_total_cost") or fast.get("total_cost") or item.get("pris"), 0)
    research = (
        (12 if fast.get("is_information_edge_candidate") else 0)
        + (10 if fast.get("is_hidden_find_candidate") else 0)
        + (10 if fast.get("mispriced_rookie_candidate") else 0)
        + (8 if fast.get("misclassified_card_candidate") else 0)
        + min(12, _n(fast.get("valuable_card_structure_score")))
        + min(10, _n((attention or {}).get("score")))
    )
    rank = min(35, max(0, _n(fast.get("rank_score"))) * 0.30)
    # Cheap cards deserve verification because small absolute resale values can
    # still be profitable, but cheapness alone is deliberately weak.
    cheap_probe = 5 if 0 < total <= 75 else (2 if 0 < total <= 150 else 0)
    # Earlier newest-first rows win otherwise-equal routing decisions.
    freshness_order = max(0, 6 - min(6, idx / 20))
    return rank + research + cheap_probe + freshness_order


def add_top5_verification_indices(candidates, selected_indices, *, hard_cap=16, reserve_slots=5, max_per_player=2):
    total = len(candidates or [])
    if not total:
        return list(selected_indices or []), []

    selected = []
    seen = set()
    for raw in selected_indices or []:
        idx = int(raw)
        if 0 <= idx < total and idx not in seen:
            selected.append(idx); seen.add(idx)

    hard_cap = max(1, int(hard_cap or 1))
    reserve_slots = max(0, min(int(reserve_slots or 0), hard_cap))
    player_counts = {}
    for idx in selected:
        fast = candidates[idx][1] or {}
        key = str(fast.get("player_name") or f"__{idx}").casefold()
        player_counts[key] = player_counts.get(key, 0) + 1

    pool = []
    for idx, candidate in enumerate(candidates):
        if idx in seen:
            continue
        fast = candidate[1] or {}
        key = str(fast.get("player_name") or f"__{idx}").casefold()
        pool.append((_priority(candidate, idx), idx, key))
    pool.sort(reverse=True)

    added = []
    for _score, idx, key in pool:
        if len(added) >= reserve_slots or len(selected) >= hard_cap:
            break
        if player_counts.get(key, 0) >= max_per_player:
            continue
        selected.append(idx); seen.add(idx); added.append(idx)
        player_counts[key] = player_counts.get(key, 0) + 1
    return selected[:hard_cap], added
