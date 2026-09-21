"""Persistent search-job store backed by Postgres.

This module contains no Streamlit state. A search job can therefore be resumed
by a new browser/session and survives Streamlit reruns. The worker that executes
jobs is deliberately separate from this persistence contract.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

import psycopg


DDL = """
CREATE TABLE IF NOT EXISTS flipfynd_search_jobs (
    job_id TEXT PRIMARY KEY,
    job_kind TEXT NOT NULL,
    signature TEXT,
    status TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS flipfynd_search_jobs_signature_idx
ON flipfynd_search_jobs(signature, updated_at DESC);
"""


def _dsn():
    return os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")


def available() -> bool:
    return bool(_dsn())


def ensure_schema():
    if not available():
        return False
    with psycopg.connect(_dsn()) as conn:
        conn.execute(DDL)
    return True


def create_job(*, job_kind: str, payload: dict, signature: str | None = None) -> dict:
    if not ensure_schema():
        raise RuntimeError("Persistent job store requires DATABASE_URL or POSTGRES_URL")
    job_id = uuid.uuid4().hex
    with psycopg.connect(_dsn()) as conn:
        conn.execute(
            """INSERT INTO flipfynd_search_jobs
               (job_id, job_kind, signature, status, progress, payload)
               VALUES (%s,%s,%s,'QUEUED',0,%s::jsonb)""",
            (job_id, job_kind, signature, json.dumps(payload, ensure_ascii=False)),
        )
    return get_job(job_id)


def get_job(job_id: str):
    if not available():
        return None
    with psycopg.connect(_dsn()) as conn:
        row = conn.execute(
            """SELECT job_id,job_kind,signature,status,progress,payload,result,error,
                      created_at,updated_at
               FROM flipfynd_search_jobs WHERE job_id=%s""", (job_id,)
        ).fetchone()
    if not row:
        return None
    keys=("job_id","job_kind","signature","status","progress","payload","result",
          "error","created_at","updated_at")
    out=dict(zip(keys,row))
    for key in ("created_at","updated_at"):
        if out[key] is not None:
            out[key]=out[key].isoformat()
    return out


def update_job(job_id: str, *, status: str | None = None, progress: int | None = None,
               result=None, error: str | None = None):
    current=get_job(job_id)
    if not current:
        return None
    new_status=status or current["status"]
    new_progress=max(0,min(100,int(progress if progress is not None else current["progress"])))
    new_result=current["result"] if result is None else result
    new_error=error if error is not None else current["error"]
    with psycopg.connect(_dsn()) as conn:
        conn.execute(
            """UPDATE flipfynd_search_jobs
               SET status=%s, progress=%s, result=%s::jsonb, error=%s, updated_at=NOW()
               WHERE job_id=%s""",
            (new_status,new_progress,
             json.dumps(new_result,ensure_ascii=False) if new_result is not None else None,
             new_error,job_id),
        )
    return get_job(job_id)


def claim_next_job(*, job_kind: str | None = None):
    """Atomically claim one queued job for an external worker.

    SKIP LOCKED lets multiple workers poll safely without executing the same
    search twice. This is the hand-off that makes work independent of a
    Streamlit websocket.
    """
    if not ensure_schema():
        return None
    with psycopg.connect(_dsn()) as conn:
        with conn.transaction():
            sql = """SELECT job_id FROM flipfynd_search_jobs
                     WHERE status='QUEUED'"""
            args = []
            if job_kind:
                sql += " AND job_kind=%s"
                args.append(job_kind)
            sql += " ORDER BY created_at ASC FOR UPDATE SKIP LOCKED LIMIT 1"
            row = conn.execute(sql, args).fetchone()
            if not row:
                return None
            job_id = row[0]
            conn.execute(
                """UPDATE flipfynd_search_jobs
                   SET status='RUNNING', progress=GREATEST(progress,1),
                       error=NULL, updated_at=NOW()
                   WHERE job_id=%s""",
                (job_id,),
            )
    return get_job(job_id)


def latest_job(*, job_kind: str, signature: str | None = None):
    """Return newest job regardless of state for UI progress/recovery."""
    if not available():
        return None
    sql = "SELECT job_id FROM flipfynd_search_jobs WHERE job_kind=%s"
    args = [job_kind]
    if signature:
        sql += " AND signature=%s"
        args.append(signature)
    sql += " ORDER BY updated_at DESC LIMIT 1"
    with psycopg.connect(_dsn()) as conn:
        row = conn.execute(sql, args).fetchone()
    return get_job(row[0]) if row else None


def latest_completed_job(*, job_kind: str, signature: str | None = None):
    if not available():
        return None
    sql="""SELECT job_id FROM flipfynd_search_jobs
           WHERE job_kind=%s AND status='COMPLETED'"""
    args=[job_kind]
    if signature:
        sql+=" AND signature=%s"
        args.append(signature)
    sql+=" ORDER BY updated_at DESC LIMIT 1"
    with psycopg.connect(_dsn()) as conn:
        row=conn.execute(sql,args).fetchone()
    return get_job(row[0]) if row else None


def latest_active_job(*, job_kind: str, signature: str | None = None):
    if not available():
        return None
    sql="""SELECT job_id FROM flipfynd_search_jobs
           WHERE job_kind=%s AND status IN ('QUEUED','RUNNING')"""
    args=[job_kind]
    if signature:
        sql+=" AND signature=%s"
        args.append(signature)
    sql+=" ORDER BY updated_at DESC LIMIT 1"
    with psycopg.connect(_dsn()) as conn:
        row=conn.execute(sql,args).fetchone()
    return get_job(row[0]) if row else None


def create_or_get_active_job(*, job_kind: str, payload: dict, signature: str) -> dict:
    """Idempotently enqueue work for one logical search.

    Streamlit reruns must not create duplicate crawls. Reuse the newest queued
    or running job for the same signature; otherwise create a new one.
    """
    active = latest_active_job(job_kind=job_kind, signature=signature)
    if active:
        return active
    return create_job(job_kind=job_kind, payload=payload, signature=signature)
