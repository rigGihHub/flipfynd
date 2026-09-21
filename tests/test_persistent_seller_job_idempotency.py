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


def test_seller_signature_is_stable_and_seller_specific():
    a = jobs.seller_job_signature("https://www.tradera.com/profile/items/1/foo", "Foo")
    b = jobs.seller_job_signature("https://www.tradera.com/profile/items/1/foo", "foo")
    c = jobs.seller_job_signature("https://www.tradera.com/profile/items/2/bar", "bar")
    assert a == b
    assert a != c
    assert a.startswith("seller_inventory:")


def test_ensure_seller_job_uses_persistent_contract(monkeypatch):
    captured = {}
    monkeypatch.setattr(jobs, "create_or_get_active_job", lambda **kwargs: captured.update(kwargs) or {"job_id": "x"})
    out = jobs.ensure_seller_inventory_job(
        profile_url="https://www.tradera.com/profile/items/1/foo",
        seller="foo",
        start_page=29,
        max_pages=120,
    )
    assert out["job_id"] == "x"
    assert captured["job_kind"] == "seller_inventory_crawl"
    assert captured["payload"]["start_page"] == 29
    assert captured["signature"].startswith("seller_inventory:")
