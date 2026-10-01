"""Bound analysis work to the amount needed for a dynamic Top 5.

Every eligible listing still participates in the cheap merit pass.  The returned
budget only limits the materially more expensive analyzer pass.  Coverage and
blind-exploration slots in ``select_fast_analysis_pool`` keep late inventory
segments represented.
"""
from __future__ import annotations


def fast_analysis_budget(total_candidates: int, *, context: str = "ordinary") -> int:
    total = max(0, int(total_candidates or 0))
    if total <= 0:
        return 0

    # Small sellers keep the existing limits. Profiles with thousands of
    # listings need broader fast triage, with bounded deep market research.
    ceiling = 160 if context == "ordinary" else (360 if total > 600 else 120)
    floor = 80 if context == "ordinary" else 60

    if total <= floor:
        return total
    # Grow gently for larger inventories, then stop.  Candidate selection still
    # sees the entire inventory before this budget is applied.
    scaled = floor + round((total - floor) ** 0.5 * (6.0 if context == "ordinary" else 5.0))
    budget = min(total, ceiling, max(floor, scaled))
    return budget


def seller_deep_analysis_budget(card_inventory_count: int) -> int:
    """Bound full seller analysis while keeping large inventories credible.

    Eight deep analyses is enough for a small seller, but not for hundreds of
    card listings. Large sellers get 60–72 slots shared across discovery routes.
    The cap bounds the market-data requests performed by full analysis.
    """
    total = max(0, int(card_inventory_count or 0))
    if total <= 0:
        return 0
    if total <= 80:
        return min(total, 8)
    if total <= 250:
        return 16
    if total <= 600:
        return 24
    return 60 if total <= 2000 else 72


__all__ = ["fast_analysis_budget", "seller_deep_analysis_budget"]
