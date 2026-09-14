"""Plan a breadth-first campaign toward a real exact-SOLD evidence base.

The campaign turns FlipFynd's per-card sold gap queue into a bounded research
batch. It never fabricates sales and never changes valuation or BUY decisions.
The default strategy is breadth first: get up to two verified exact sales for an
identity before spending effort on deeper history for that same card.
"""
from __future__ import annotations

from src.comp_acquisition_router import build_comp_acquisition_router
from src.sold_comp_intake import review_sold_comp_intake
from src.sold_gap_planner import build_sold_research_queue


def _norm(value) -> str:
    return " ".join(str(value or "").casefold().strip().split())


def _identity_key(identity: dict | None):
    identity = identity or {}
    core = tuple(_norm(identity.get(key)) for key in ("player_name", "set_name", "season", "card_number"))
    if not all(core):
        return None
    variant = tuple(_norm(identity.get(key)) for key in ("parallel", "serial_denominator", "grading_company", "grade"))
    return core + variant


def _exact_ready_count(records) -> int:
    count = 0
    for row in records or []:
        if not isinstance(row, dict):
            continue
        try:
            review = review_sold_comp_intake(row)
        except Exception:
            continue
        if review.get("exact_identity_ready"):
            count += 1
    return count


def build_exact_sold_campaign(
    candidates,
    sold_records,
    *,
    target: int = 100,
    batch_size: int = 10,
    per_identity_target: int = 2,
) -> dict:
    """Build the next bounded exact-SOLD research batch.

    ``target`` is the desired total number of exact-ready realised sales in the
    evidence store. ``per_identity_target`` defaults to two so early collection
    spreads across many cards instead of overfitting to a few easy identities.
    """
    target = max(1, int(target or 100))
    batch_size = max(1, min(int(batch_size or 10), 50))
    per_identity_target = max(1, min(int(per_identity_target or 2), 5))
    records = [row for row in (sold_records or []) if isinstance(row, dict)]

    exact_ready = _exact_ready_count(records)
    remaining = max(0, target - exact_ready)
    if remaining == 0:
        return {
            "status": "TARGET_REACHED",
            "target": target,
            "exact_ready_count": exact_ready,
            "remaining_to_target": 0,
            "tasks": [],
            "batch_size": 0,
            "note": "Målet är nått med exact-ready realiserade sales; inga extra sales har antagits eller skapats.",
        }

    queue = build_sold_research_queue(candidates or [], records, limit=max(50, len(candidates or [])))
    unique = {}
    for row in queue.get("rows") or []:
        if row.get("status") not in {"NO_EXACT_SOLD", "THIN_EXACT_SOLD"}:
            continue
        key = _identity_key(row.get("identity"))
        if not key:
            continue
        previous = unique.get(key)
        if previous is None or float(row.get("priority_score") or 0) > float(previous.get("priority_score") or 0):
            unique[key] = row

    identities = list(unique.values())
    identities.sort(key=lambda row: (
        int(row.get("exact_sold_count") or 0),
        -float(row.get("priority_score") or 0),
        str(row.get("title") or ""),
    ))

    # Breadth-first rounds: every zero-comp identity gets one research slot before
    # any of them gets a second slot. Thin identities only need the missing slots.
    task_pool = []
    for research_round in range(1, per_identity_target + 1):
        for row in identities:
            current = int(row.get("exact_sold_count") or 0)
            needed = max(0, per_identity_target - current)
            if research_round > needed:
                continue
            router = build_comp_acquisition_router(row.get("identity") or {}, records)
            next_source = router.get("next_source") or {}
            task_pool.append({
                "title": row.get("title"),
                "url": row.get("url"),
                "identity": row.get("identity") or {},
                "current_exact_sold": current,
                "desired_exact_sold": per_identity_target,
                "research_round": research_round,
                "priority_score": float(row.get("priority_score") or 0),
                "route_status": router.get("status"),
                "query": router.get("query"),
                "next_source_key": next_source.get("key"),
                "next_source_label": next_source.get("label"),
                "next_source_url": next_source.get("url"),
                "reason": router.get("reason"),
            })

    take = min(batch_size, remaining, len(task_pool))
    tasks = task_pool[:take]
    identity_blocked = int(queue.get("identity_first_count") or 0)
    if tasks:
        status = "RESEARCH_ACTIVE"
    elif identity_blocked:
        status = "IDENTITY_BLOCKED"
    else:
        status = "NO_ACTIONABLE_IDENTITIES"

    return {
        "status": status,
        "target": target,
        "exact_ready_count": exact_ready,
        "remaining_to_target": remaining,
        "batch_size": len(tasks),
        "tasks": tasks,
        "actionable_identity_count": len(identities),
        "identity_blocked_count": identity_blocked,
        "per_identity_target": per_identity_target,
        "queue_summary": {
            "no_exact_sold_count": int(queue.get("no_exact_sold_count") or 0),
            "thin_exact_sold_count": int(queue.get("thin_exact_sold_count") or 0),
            "has_exact_sold_count": int(queue.get("has_exact_sold_count") or 0),
        },
        "note": "Kampanjen planerar bara research. En task blir inte en SOLD-comp förrän en faktisk realiserad försäljning har verifierats och passerat intake-gaten.",
    }
