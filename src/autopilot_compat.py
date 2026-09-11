"""Deployment-safe Market Coverage Autopilot compatibility wrapper."""
from __future__ import annotations
import inspect


def build_autopilot_plan_compat(
    planner,
    coverage_h,
    coverage_f,
    refresh_h,
    refresh_f,
    *,
    analyzed_results=None,
):
    """Call either the new or legacy planner signature without crashing.

    Streamlit Cloud can briefly run a newly deployed app.py against an older
    imported module during redeploy/reload. We inspect the loaded callable
    instead of deliberately triggering TypeError.
    """
    try:
        params = inspect.signature(planner).parameters
    except (TypeError, ValueError):
        params = {}

    if "analyzed_results" in params:
        return planner(
            coverage_h,
            coverage_f,
            refresh_h,
            refresh_f,
            analyzed_results=analyzed_results or [],
        )

    return planner(
        coverage_h,
        coverage_f,
        refresh_h,
        refresh_f,
    )
