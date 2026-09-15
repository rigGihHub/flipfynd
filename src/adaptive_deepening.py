from src.seller_collector_signals import collector_signals


def _independent_value_signal(candidate):
    item, fast, attention = candidate
    attention_score = int((attention or {}).get("score", 0) or 0)
    demand_boost = int(fast.get("player_card_demand_preselection_boost", 0) or 0)
    review_priority = int(fast.get("player_card_demand_review_priority_score", 0) or 0)
    title_signal = int(collector_signals(item or {}).get("score") or 0)
    return attention_score >= 12 or demand_boost >= 8 or review_priority >= 12 or title_signal >= 10


def dynamic_deep_analysis_cap(candidates, base_limit=12, floor=48, max_cap=96):
    """Size the expensive pass from actual value signals, not a fixed Top N."""
    total = len(candidates or [])
    if not total:
        return 0
    signaled = sum(1 for candidate in candidates if _independent_value_signal(candidate))
    target = max(int(base_limit or 1), int(floor or 1), int(base_limit or 1) + signaled)
    return min(total, max(int(base_limit or 1), min(int(max_cap or target), target)))


def select_dynamic_seller_deep_rows(rows, base_limit=8, max_cap=20):
    """Build a small adaptive pool for a final Top 5.

    The quick pass still scans the complete seller inventory. Full analysis is
    reserved for the leading rows plus a bounded number of later rows carrying
    evidence that can realistically overturn the current Top 5.
    """
    rows = list(rows or [])
    baseline = rows[:max(1, int(base_limit or 1))]
    selected = list(baseline)
    selected_ids = {id(row) for row in selected}
    for row in rows[len(baseline):]:
        if len(selected) >= max(int(base_limit or 1), int(max_cap or base_limit)):
            break
        decision = str(row.get("decision") or "").upper()
        credible = (
            int(row.get("collector_signal_score") or 0) >= 10
            or int(row.get("sold_comps") or 0) > 0
            or decision.startswith(("KÖP", "UNDERSÖK"))
            or float(row.get("market_edge") or 0) >= 55
        )
        if credible and id(row) not in selected_ids:
            selected.append(row)
            selected_ids.add(id(row))
    return selected


def select_adaptive_full_analysis_indices(candidates, base_limit=12, hard_cap=30):
    """Select candidates for expensive full analysis without changing valuation.

    The old top-N baseline is always retained. Extra candidates are deepened
    only when their fast score is close to the baseline cutoff or they carry
    an independent scarcity/demand/review signal.
    """
    total = len(candidates)
    if total <= 0:
        return []
    base_limit = max(1, int(base_limit or 1))
    hard_cap = max(base_limit, int(hard_cap or base_limit))
    selected = list(range(min(base_limit, total)))
    if total <= base_limit or len(selected) >= hard_cap:
        return selected

    cutoff_fast = float(candidates[min(base_limit, total) - 1][1].get("rank_score", 0) or 0)
    near_cutoff = cutoff_fast * 0.85 if cutoff_fast > 0 else None

    for idx in range(base_limit, total):
        if len(selected) >= hard_cap:
            break
        _item, fast, attention = candidates[idx]
        fast_score = float(fast.get("rank_score", 0) or 0)
        close_enough = near_cutoff is not None and fast_score >= near_cutoff
        independent_signal = _independent_value_signal(candidates[idx])
        if close_enough or independent_signal:
            selected.append(idx)
    return selected
