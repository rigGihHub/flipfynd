"""Background worker entry point for persistent FlipFynd jobs.

Run as a separate process/service:
    python worker.py

The worker is deliberately independent of Streamlit. Job-specific executors
are registered here as they become safe to run headlessly.
"""
from __future__ import annotations

import os
import time
import traceback

from src.persistent_search_jobs import claim_next_job, update_job
from src.public_seller_inventory import crawl_public_seller_inventory

POLL_SECONDS = max(1, int(os.getenv("FLIPFYND_WORKER_POLL_SECONDS", "3")))


def execute_job(job: dict):
    kind = str(job.get("job_kind") or "")
    payload = dict(job.get("payload") or {})

    if kind == "healthcheck":
        return {"ok": True, "worker": "flipfynd", "payload": payload}

    if kind == "seller_inventory_crawl":
        profile_url = str(payload.get("profile_url") or "").strip()
        if not profile_url:
            raise ValueError("seller_inventory_crawl requires profile_url")
        return crawl_public_seller_inventory(
            profile_url,
            start_page=int(payload.get("start_page") or 1),
            max_pages=int(payload.get("max_pages") or 120),
            timeout=int(payload.get("timeout") or 8),
            fallback_alias=str(payload.get("seller") or "").strip() or None,
            paging_size=payload.get("paging_size"),
        )

    raise RuntimeError(f"Unsupported background job kind: {kind}")


def run_once() -> bool:
    job = claim_next_job()
    if not job:
        return False
    job_id = job["job_id"]
    try:
        update_job(job_id, status="RUNNING", progress=5)
        result = execute_job(job)
        update_job(job_id, status="COMPLETED", progress=100, result=result, error="")
    except Exception as exc:
        update_job(
            job_id,
            status="FAILED",
            progress=int(job.get("progress") or 0),
            error=f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=8)}",
        )
    return True


def main():
    while True:
        if not run_once():
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
