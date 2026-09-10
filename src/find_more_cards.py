"""Safe analysis deepening for FlipFynd.

Selects more already-filtered candidates for the existing full analysis when
the first deep pass produces no BUY. It never changes filters, thresholds,
valuation, ranking or decisions.
"""
from __future__ import annotations


def select_second_pass_indices(candidate_count, already_selected, *, extra_limit=12, total_hard_cap=45):
    selected = {int(i) for i in (already_selected or []) if int(i) >= 0}
    room = max(0, int(total_hard_cap) - len(selected))
    take = min(max(0, int(extra_limit)), room)
    if take <= 0:
        return []
    return [
        idx for idx in range(max(0, int(candidate_count)))
        if idx not in selected
    ][:take]
