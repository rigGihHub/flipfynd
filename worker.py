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
from src.seller_checkpoint_store import load_checkpoint, save_checkpoint
from src.seller_top5_controller import _checkpoint_key

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
        seller = str(payload.get("seller") or "").strip()
        database_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
        checkpoint_key = _checkpoint_key(seller, profile_url)
        checkpoint = load_checkpoint(checkpoint_key, database_url=database_url) or {}
        start_page = max(
            int(payload.get("start_page") or 1),
            int(checkpoint.get("next_page") or 1),
        )
        result = crawl_public_seller_inventory(
            profile_url,
            start_page=start_page,
            max_pages=int(payload.get("max_pages") or 120),
            timeout=int(payload.get("timeout") or 8),
            fallback_alias=seller or None,
            paging_size=checkpoint.get("total_listing_estimate") or payload.get("paging_size"),
        )
        # Merge worker output with everything already persisted. A worker
        # restart or browser disconnect must never discard earlier pages.
        items = dict(checkpoint.get("items") or {})
        for item in result.get("items") or []:
            key = str(item.get("tradera_item_id") or item.get("lank") or "").strip()
            if key:
                items[key] = item
        next_page = int(result.get("next_page") or start_page)
        durable = {
            "next_page": next_page,
            "pages_read": max(0, next_page - 1),
            "items": items,
            "total_listing_estimate": result.get("total_listing_estimate") or checkpoint.get("total_listing_estimate"),
        }
        save_checkpoint(checkpoint_key, durable, database_url=database_url)
        result = dict(result)
        result["items"] = list(items.values())
        result["inventory_count"] = len(items)
        result["checkpoint"] = durable
        return result

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
