"""Single-worker background queue for non-blocking seller searches."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import time
from uuid import uuid4

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="flipfynd-seller")
_lock = Lock()
_jobs: dict[str, dict] = {}


def submit_seller_job(task) -> str:
    job_id = uuid4().hex
    with _lock:
        _jobs[job_id] = {"status": "QUEUED", "progress": {}, "result": None, "error": None, "created_at": time()}

    def progress(payload):
        with _lock:
            if job_id in _jobs:
                _jobs[job_id]["progress"] = dict(payload or {})

    def run():
        with _lock:
            _jobs[job_id]["status"] = "RUNNING"
        try:
            result = task(progress)
        except Exception as exc:
            with _lock:
                _jobs[job_id].update(status="FAILED", error=str(exc))
        else:
            with _lock:
                _jobs[job_id].update(status="COMPLETE", result=result)

    _executor.submit(run)
    return job_id


def seller_job_snapshot(job_id: str | None) -> dict:
    if not job_id:
        return {"status": "NONE"}
    with _lock:
        job = _jobs.get(str(job_id))
        if not job:
            return {"status": "MISSING"}
        return {
            "status": job["status"],
            "progress": dict(job.get("progress") or {}),
            "result": job.get("result"),
            "error": job.get("error"),
        }


def discard_seller_job(job_id: str | None) -> None:
    if not job_id:
        return
    with _lock:
        _jobs.pop(str(job_id), None)
