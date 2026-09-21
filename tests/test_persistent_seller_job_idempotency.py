from src import persistent_search_jobs as jobs


def test_create_or_get_active_job_reuses_running_job(monkeypatch):
    active = {"job_id": "existing", "status": "RUNNING"}
    monkeypatch.setattr(jobs, "latest_active_job", lambda **kwargs: active)
    monkeypatch.setattr(jobs, "create_job", lambda **kwargs: (_ for _ in ()).throw(AssertionError("duplicate job")))
    assert jobs.create_or_get_active_job(
        job_kind="seller_inventory_crawl",
        payload={"profile_url": "https://www.tradera.com/profile/items/1/foo"},
        signature="seller:1",
    ) is active


def test_create_or_get_active_job_creates_when_none_exists(monkeypatch):
    monkeypatch.setattr(jobs, "latest_active_job", lambda **kwargs: None)
    monkeypatch.setattr(jobs, "create_job", lambda **kwargs: {"job_id": "new", **kwargs})
    created = jobs.create_or_get_active_job(
        job_kind="seller_inventory_crawl",
        payload={"profile_url": "https://www.tradera.com/profile/items/1/foo"},
        signature="seller:1",
    )
    assert created["job_id"] == "new"
    assert created["signature"] == "seller:1"
