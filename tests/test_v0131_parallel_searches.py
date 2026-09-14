from threading import Event
from time import sleep

from src.seller_background_jobs import discard_seller_job, seller_job_snapshot, submit_seller_job


def test_seller_job_returns_immediately_and_completes_in_background():
    release = Event()

    def task(progress):
        progress({"phase": "full_progress", "done": 3, "total": 10, "percent": 72})
        release.wait(timeout=2)
        return {"status": "READY", "rows": []}

    job_id = submit_seller_job(task)
    assert seller_job_snapshot(job_id)["status"] in {"QUEUED", "RUNNING"}
    release.set()
    for _ in range(200):
        snapshot = seller_job_snapshot(job_id)
        if snapshot["status"] == "COMPLETE":
            break
        sleep(0.005)
    assert snapshot["result"]["status"] == "READY"
    discard_seller_job(job_id)


def test_ui_explicitly_keeps_main_search_available():
    app = open("app.py", encoding="utf-8").read()
    assert "Du kan använda den vanliga sökningen samtidigt." in app
    assert "disabled=_seller_running" in app
    assert 'APP_VERSION = "v0.13.1"' in app
