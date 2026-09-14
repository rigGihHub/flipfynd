"""One backend entry point for FlipFynd's verified exact-SOLD acquisition program.

The program combines evidence-store health with the next breadth-first research
batch. It is planning/diagnostics only: no task becomes a comp until a realised
sale has been verified and passed the normal SOLD + identity gates.
"""
from __future__ import annotations

from src.exact_sold_campaign import build_exact_sold_campaign
from src.sold_evidence_health import build_sold_evidence_health


def build_sold_acquisition_program(
    candidates,
    sold_records,
    *,
    target_floor: int = 50,
    target_goal: int = 100,
    batch_size: int = 10,
    per_identity_target: int = 2,
) -> dict:
    """Return current evidence health plus the next safe research batch."""
    health = build_sold_evidence_health(
        sold_records,
        target_floor=target_floor,
        target_goal=target_goal,
    )

    # Work toward the first meaningful milestone before expanding to 100. Once
    # 50 exact-ready sales exist, the same engine continues toward the full goal.
    campaign_target = target_floor if health["exact_ready_count"] < target_floor else target_goal
    campaign = build_exact_sold_campaign(
        candidates,
        sold_records,
        target=campaign_target,
        batch_size=batch_size,
        per_identity_target=per_identity_target,
    )

    if health["exact_ready_count"] >= target_goal:
        phase = "GOAL_COMPLETE"
    elif health["exact_ready_count"] >= target_floor:
        phase = "EXPAND_TO_GOAL"
    else:
        phase = "BUILD_TO_FLOOR"

    return {
        "phase": phase,
        "health": health,
        "campaign": campaign,
        "exact_ready_count": health["exact_ready_count"],
        "current_target": campaign_target,
        "remaining_to_current_target": max(0, campaign_target - health["exact_ready_count"]),
        "next_tasks": list(campaign.get("tasks") or []),
        "next_task_count": len(campaign.get("tasks") or []),
        "note": "Programmet räknar endast verifierade exact-ready realiserade sales. Researchuppgifter är inte comps förrän intake-gaten har passerats.",
    }
