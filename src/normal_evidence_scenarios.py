"""Evidence scenarios for the normal analyzer result.

The normal market-analysis payload contains both realised sales and active
listings. This adapter deliberately accepts only rows marked ``sold`` and
re-checks the independent-observation quality gate before exposing an interval.
It never creates a value and never changes a BUY decision.
"""
from __future__ import annotations

from typing import Any, Iterable

from src.comp_quality_guard import build_comp_quality_guard
from src.evidence_scenario_range import build_evidence_scenario_range


def build_normal_evidence_scenario_range(
    *,
    valuation_basis: str | None,
    comparable_details: Iterable[dict] | None,
    total_cost: float | None = None,
    identity_verified: bool = False,
    premium_identity: bool = False,
    premium_exact_comps: Iterable[dict] | None = None,
) -> dict[str, Any]:
    """Build an evidence-only interval for a normal analysis result.

    ``premium_exact_comps`` is already classified by Premium Comp Hunter and is
    used instead of broad same-player comps for premium cards. For base cards,
    only market details explicitly marked ``market_state == 'sold'`` survive.
    """
    if str(valuation_basis or "").casefold() != "sold":
        return {
            "status": "BLOCKED",
            "available": False,
            "note": "Scenariointerval kräver verifierade SOLD-comps; aktiva annonser är endast researchsignal.",
        }
    if not identity_verified:
        return {
            "status": "BLOCKED",
            "available": False,
            "note": "Scenariointerval kräver att exakt kortidentitet är verifierad.",
        }

    if premium_identity:
        rows = [dict(row) for row in (premium_exact_comps or []) if isinstance(row, dict)]
    else:
        rows = [
            dict(row)
            for row in (comparable_details or [])
            if isinstance(row, dict) and str(row.get("market_state") or "").casefold() == "sold"
        ]

    quality = build_comp_quality_guard(rows)
    result = build_evidence_scenario_range(
        rows,
        total_cost=total_cost,
        decision_grade=bool(quality.get("decision_grade")),
    )
    result["quality_guard_status"] = quality.get("status")
    result["quality_guard_blockers"] = list(quality.get("blockers") or [])
    result["quality_guard_warnings"] = list(quality.get("warnings") or [])
    result["evidence_type"] = "exact_premium_sold" if premium_identity else "exact_sold"
    if not result.get("available"):
        result["note"] = (
            "Scenariointerval låst tills Exact SOLD-underlaget är decision-grade. "
            + "; ".join((quality.get("blockers") or [])[:2])
        )
    return result
