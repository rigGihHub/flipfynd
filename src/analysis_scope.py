"""Bounded recent-first coverage across the saved market archive."""
from __future__ import annotations

from src.fast_analysis_pool import select_fast_analysis_pool


def _listing_key(item: dict) -> str:
    for key in ("tradera_item_id", "id", "item_id", "lank", "url", "link"):
        value = (item or {}).get(key)
        if value not in (None, ""):
            return f"{key}:{str(value).strip()}"
    return "title:" + "|".join(
        str((item or {}).get(key) or "").strip().casefold()
        for key in ("titel", "title", "pris", "frakt")
    )


def select_recent_archive_fast_pool(
    eligible_items,
    latest_items,
    *,
    cap: int,
    include_older: bool = False,
    archive_fraction: float = 0.25,
):
    """Select a bounded pool while reserving coverage for saved older ads.

    Default searches remain recent-first. When an archive exists, one quarter
    of the same fixed fast-analysis budget is reserved for it, so thousands of
    saved listings are not silently excluded. Explicit archive mode lets all
    listings compete in the shared selector. This function changes only
    routing; it creates no value, profit, score or BUY decision.
    """
    eligible = [row for row in (eligible_items or []) if isinstance(row, dict)]
    cap = max(0, min(int(cap or 0), len(eligible)))
    latest_keys = {_listing_key(row) for row in (latest_items or []) if isinstance(row, dict)}
    recent = [row for row in eligible if _listing_key(row) in latest_keys]
    archive = [row for row in eligible if _listing_key(row) not in latest_keys]

    if cap <= 0:
        selected = []
    elif include_older or not recent or not archive:
        selected = select_fast_analysis_pool(eligible, cap=cap, exploration_fraction=0.25)
    else:
        archive_slots = min(len(archive), max(1, round(cap * float(archive_fraction))))
        recent_slots = min(len(recent), cap - archive_slots)
        archive_slots = min(len(archive), cap - recent_slots)
        selected = select_fast_analysis_pool(
            recent, cap=recent_slots, exploration_fraction=0.25
        ) + select_fast_analysis_pool(
            archive, cap=archive_slots, exploration_fraction=0.35
        )

        # If either lane was smaller than its reservation, fill unused capacity
        # from the remaining globally ranked pool without duplicates.
        seen = {_listing_key(row) for row in selected}
        remainder = [row for row in eligible if _listing_key(row) not in seen]
        if len(selected) < cap and remainder:
            selected += select_fast_analysis_pool(
                remainder, cap=cap - len(selected), exploration_fraction=0.25
            )

    selected_latest = sum(_listing_key(row) in latest_keys for row in selected)
    return selected[:cap], {
        "latest_eligible_candidates": len(recent),
        "archive_eligible_candidates": len(archive),
        "latest_fast_selected": selected_latest,
        "archive_fast_selected": len(selected[:cap]) - selected_latest,
        "automatic_archive_coverage": bool(not include_older and recent and archive),
    }


__all__ = ["select_recent_archive_fast_pool"]
