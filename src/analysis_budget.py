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

    # Five displayed cards do not justify hundreds of equivalent analyses.
    # Seller scans use a slightly smaller ceiling because they can run beside
    # an ordinary search and commonly contain many near-duplicate listings.
    ceiling = 160 if context == "ordinary" else 120
    floor = 80 if context == "ordinary" else 60

    if total <= floor:
        return total
    # Grow gently for larger inventories, then stop.  Candidate selection still
    # sees the entire inventory before this budget is applied.
    scaled = floor + round((total - floor) ** 0.5 * (2.0 if context == "ordinary" else 1.6))
    return min(total, ceiling, max(floor, scaled))


__all__ = ["fast_analysis_budget"]
