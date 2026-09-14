"""Summarise the health and progress of FlipFynd's realised-sale evidence store.

This module is diagnostic only. It does not create comps, repair ambiguous rows,
change valuations, or upgrade BUY decisions. Its purpose is to make the 50–100
verified exact-SOLD objective measurable from whatever persistent runtime data
the app has loaded.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable

from src.sold_comp_intake import sold_comp_intake_audit
from src.sold_comp_quality import audit_sold_comp_records


def build_sold_evidence_health(records: Iterable[dict] | None, *, target_floor: int = 50, target_goal: int = 100) -> dict:
    rows = [dict(row) for row in (records or []) if isinstance(row, dict)]
    floor = max(1, int(target_floor or 50))
    goal = max(floor, int(target_goal or 100))

    quality = audit_sold_comp_records(rows)
    intake = sold_comp_intake_audit(rows)

    exact_ready = int(intake.get("exact_ready_count") or 0)
    safe_sales = int(quality.get("safe_count") or 0)
    blocked = int(quality.get("blocked_count") or 0)
    identity_review = int(intake.get("identity_review_count") or 0)
    sale_only = int(intake.get("sale_only_count") or 0)
    rejected = int(intake.get("rejected_count") or 0)

    blocked_reasons = Counter(quality.get("rejection_reasons") or {})
    contradictory = int(blocked_reasons.get("contradictory_unsold_state", 0))

    if exact_ready >= goal:
        status = "GOAL_REACHED"
    elif exact_ready >= floor:
        status = "FLOOR_REACHED"
    elif safe_sales == 0:
        status = "NO_SAFE_SALES"
    elif exact_ready == 0:
        status = "NO_EXACT_READY"
    else:
        status = "BUILDING"

    exact_share = (exact_ready / safe_sales) if safe_sales else 0.0
    blocked_share = (blocked / len(rows)) if rows else 0.0

    return {
        "status": status,
        "total_records": len(rows),
        "safe_sale_count": safe_sales,
        "exact_ready_count": exact_ready,
        "identity_review_count": identity_review,
        "sale_only_count": sale_only,
        "rejected_count": rejected,
        "blocked_quality_count": blocked,
        "contradictory_status_count": contradictory,
        "exact_ready_share_of_safe_sales": round(exact_share, 4),
        "blocked_share": round(blocked_share, 4),
        "target_floor": floor,
        "target_goal": goal,
        "remaining_to_floor": max(0, floor - exact_ready),
        "remaining_to_goal": max(0, goal - exact_ready),
        "floor_progress_pct": round(min(100.0, exact_ready / floor * 100.0), 1),
        "goal_progress_pct": round(min(100.0, exact_ready / goal * 100.0), 1),
        "quality_rejection_reasons": dict(blocked_reasons),
        "intake_status_counts": dict(intake.get("status_counts") or {}),
        "note": "Bara exact-ready, verifierade realiserade sales räknas mot 50/100-målet. Prisguider och blockerade poster räknas inte.",
    }
