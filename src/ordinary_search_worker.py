"""Executable ordinary-search worker entrypoint.

The analysis callable is injected so the large Streamlit app is not imported by
the worker. This keeps UI state out of background execution.
"""
from __future__ import annotations

from src.loader import load_data


def execute_ordinary_search_job(payload: dict, progress, *, analyze_fn):
    progress(5)
    data=load_data()
    progress(10)
    if not data:
        return {"results": [], "debug": {"worker_status": "NO_DATA", "final_results": 0}}
    results,debug=analyze_fn(
        data=data,
        sport=payload["sport"],
        search=payload.get("search") or "",
        max_price=float(payload["max_price"]),
        sale_type=payload["sale_type"],
        full_limit=int(payload["full_limit"]),
        strategy=payload["strategy"],
        numbered_only=bool(payload.get("numbered_only")),
        patch_only=bool(payload.get("patch_only")),
        auto_only=bool(payload.get("auto_only")),
        include_older=bool(payload.get("include_older")),
    )
    progress(95)
    debug=dict(debug or {})
    debug["worker_status"]="COMPLETED"
    debug["background_job"]=True
    return {"results": list(results or []), "debug": debug}


__all__=["execute_ordinary_search_job"]
