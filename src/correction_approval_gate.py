"""Manual approval gate for FlipFynd model-correction candidates.

Only candidates that passed holdout validation can become REVIEW_READY.
Nothing in this module changes production behavior.
"""
from __future__ import annotations

MIN_HOLDOUT_TOTAL = 5
MIN_IMPROVEMENT_PCT = 5.0

def _metric_summary(metrics):
    out=[]
    for name,m in (metrics or {}).items():
        if not m.get("eligible"):
            continue
        out.append({
            "metric":name,
            "discovery_count":m.get("discovery_count"),
            "holdout_count":m.get("holdout_count"),
            "shift":m.get("shift"),
            "mae_before":m.get("mae_before"),
            "mae_after":m.get("mae_after"),
            "improvement_pct":m.get("improvement_pct"),
            "passes":bool(m.get("passes")),
        })
    return out

def review_correction_candidate(holdout_result):
    metrics=_metric_summary((holdout_result or {}).get("metrics"))
    passed=bool((holdout_result or {}).get("passes_holdout"))
    holdout_count=int((holdout_result or {}).get("holdout_count") or 0)
    all_metrics_pass=bool(metrics) and all(m["passes"] for m in metrics)
    min_improvement=min(
        [float(m["improvement_pct"]) for m in metrics if m.get("improvement_pct") is not None],
        default=None
    )

    blockers=[]
    if not passed:
        blockers.append("Klarade inte holdout-testet")
    if holdout_count < MIN_HOLDOUT_TOTAL:
        blockers.append("För få holdout-utfall")
    if not metrics:
        blockers.append("Inga testbara mått")
    elif not all_metrics_pass:
        blockers.append("Alla mått förbättrades inte")
    if min_improvement is not None and min_improvement < MIN_IMPROVEMENT_PCT:
        blockers.append("För liten förbättring")

    status="REVIEW_READY" if not blockers else "NOT_READY"
    return {
        "segment":(holdout_result or {}).get("segment"),
        "label":(holdout_result or {}).get("label"),
        "status":status,
        "ready_for_manual_review":status=="REVIEW_READY",
        "metrics":metrics,
        "blockers":blockers,
        "discovery_count":int((holdout_result or {}).get("discovery_count") or 0),
        "holdout_count":holdout_count,
        "minimum_improvement_pct":round(min_improvement,1) if min_improvement is not None else None,
        "automatic_change":False,
        "production_enabled":False,
    }

def build_correction_approval_gate(holdout_validation):
    reviews=[review_correction_candidate(r) for r in (holdout_validation or {}).get("results",[])]
    ready=[r for r in reviews if r["ready_for_manual_review"]]
    return {
        "candidate_count":len(reviews),
        "review_ready_count":len(ready),
        "reviews":reviews,
        "review_ready":ready,
        "automatic_model_changes":False,
        "production_changes":False,
        "note":"Endast korrigeringar som klarat separat holdout-test kan bli Redo att överväga. Statusen aktiverar aldrig ändringen i produktion.",
    }
