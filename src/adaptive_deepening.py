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
        attention_score = int((attention or {}).get("score", 0) or 0)
        demand_boost = int(fast.get("player_card_demand_preselection_boost", 0) or 0)
        review_priority = int(fast.get("player_card_demand_review_priority_score", 0) or 0)
        close_enough = near_cutoff is not None and fast_score >= near_cutoff
        independent_signal = attention_score >= 12 or demand_boost >= 8 or review_priority >= 12
        if close_enough or independent_signal:
            selected.append(idx)
    return selected
