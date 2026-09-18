"""Serializable contract between Streamlit and the ordinary-search worker."""
from __future__ import annotations


def build_ordinary_search_job_payload(*, sport, search, max_price, sale_type,
                                      full_limit, strategy, numbered_only,
                                      patch_only, auto_only, include_older,
                                      data_version, app_version):
    return {
        "sport": str(sport),
        "search": str(search or ""),
        "max_price": float(max_price),
        "sale_type": str(sale_type),
        "full_limit": int(full_limit),
        "strategy": str(strategy),
        "numbered_only": bool(numbered_only),
        "patch_only": bool(patch_only),
        "auto_only": bool(auto_only),
        "include_older": bool(include_older),
        "data_version": str(data_version),
        "app_version": str(app_version),
    }


def unpack_completed_ordinary_job(job):
    if not isinstance(job, dict) or job.get("status") != "COMPLETED":
        return None
    result=job.get("result")
    if not isinstance(result, dict):
        return None
    rows=result.get("results")
    debug=result.get("debug")
    if not isinstance(rows, list) or not isinstance(debug, dict):
        return None
    return rows, debug


__all__=["build_ordinary_search_job_payload","unpack_completed_ordinary_job"]
