"""Guarantee full-analysis coverage for distinct collector value drivers.

The selection layer only routes existing candidates into the ordinary full
analyser.  It never creates card facts, valuations, scores or decisions.
"""
from __future__ import annotations

from src.seller_collector_signals import collector_signals


SIGNAL_ORDER = (
    "autograph",
    "one_of_one",
    "serial_numbered",
    "patch_relic",
    "case_hit_ssp",
    "error_variation",
)


def add_collector_signal_coverage_indices(
    candidates,
    selected_indices,
    *,
    extra_slots=6,
    hard_cap=30,
):
    """Add the strongest omitted candidate for each important signal family."""
    rows = list(candidates or [])
    selected = {int(i) for i in (selected_indices or []) if 0 <= int(i) < len(rows)}
    room = min(max(0, int(extra_slots)), max(0, int(hard_cap) - len(selected)))
    if room <= 0:
        return list(selected_indices or []), []

    added = []
    for signal_name in SIGNAL_ORDER:
        if len(added) >= room:
            break
        if any(
            signal_name in set(collector_signals(rows[idx][0] or {}).get("signals") or [])
            for idx in selected
        ):
            continue
        matches = [
            idx for idx, (item, _fast, _attention) in enumerate(rows)
            if idx not in selected
            and signal_name in set(collector_signals(item or {}).get("signals") or [])
        ]
        if not matches:
            continue
        best = max(
            matches,
            key=lambda idx: (
                float((rows[idx][1] or {}).get("rank_score") or 0),
                float((rows[idx][1] or {}).get("player_market_score") or 0),
                -idx,
            ),
        )
        selected.add(best)
        added.append(best)

    return list(selected_indices or []) + added, added
