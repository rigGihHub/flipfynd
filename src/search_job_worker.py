"""Claim and execute persistent FlipFynd jobs.

The worker process is intentionally independent of Streamlit. Deployment can
run it as a separate worker service; browser disconnects then have no effect on
the claimed job.
"""
from __future__ import annotations

import os
import time
import traceback

import psycopg

from src.persistent_search_jobs import ensure_schema, get_job, update_job


def claim_next_job(job_kind: str = "ordinary_search"):
    dsn=os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if not dsn or not ensure_schema():
        return None
    with psycopg.connect(dsn) as conn:
        with conn.transaction():
            row=conn.execute(
                """SELECT job_id FROM flipfynd_search_jobs
                   WHERE job_kind=%s AND status='QUEUED'
                   ORDER BY created_at
                   FOR UPDATE SKIP LOCKED LIMIT 1""", (job_kind,)
            ).fetchone()
            if not row:
                return None
            conn.execute(
                """UPDATE flipfynd_search_jobs
                   SET status='RUNNING',progress=1,updated_at=NOW()
                   WHERE job_id=%s""", (row[0],)
            )
    return get_job(row[0])


def run_claimed_job(job: dict, handler):
    job_id=job["job_id"]
    try:
        def progress(value):
            update_job(job_id,status="RUNNING",progress=value)
        result=handler(dict(job.get("payload") or {}), progress)
        return update_job(job_id,status="COMPLETED",progress=100,result=result,error="")
    except Exception as exc:
        update_job(job_id,status="FAILED",error=f"{type(exc).__name__}: {exc}")
        return None


def worker_loop(handler, *, poll_seconds=2):
    while True:
        job=claim_next_job()
        if job:
            run_claimed_job(job,handler)
        else:
            time.sleep(max(1,int(poll_seconds)))


__all__=["claim_next_job","run_claimed_job","worker_loop"]
