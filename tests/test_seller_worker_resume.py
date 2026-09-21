import worker


def test_seller_worker_resumes_furthest_checkpoint_and_merges(monkeypatch):
    old = {
        "next_page": 29,
        "pages_read": 28,
        "items": {"old": {"tradera_item_id": "old"}},
        "total_listing_estimate": 9000,
    }
    saved = {}
    monkeypatch.setattr(worker, "load_checkpoint", lambda *a, **k: old)
    monkeypatch.setattr(worker, "save_checkpoint", lambda key, value, **k: saved.update(value))
    seen = {}

    def crawl(url, **kwargs):
        seen.update(kwargs)
        return {
            "ok": True,
            "items": [{"tradera_item_id": "new"}],
            "next_page": 30,
            "total_listing_estimate": 9000,
        }

    monkeypatch.setattr(worker, "crawl_public_seller_inventory", crawl)
    result = worker.execute_job({
        "job_kind": "seller_inventory_crawl",
        "payload": {
            "profile_url": "https://www.tradera.com/profile/items/123/foo",
            "seller": "foo",
            "start_page": 1,
        },
    })
    assert seen["start_page"] == 29
    assert result["inventory_count"] == 2
    assert result["checkpoint"]["next_page"] == 30
    assert result["checkpoint"]["pages_read"] == 29
    assert set(result["checkpoint"]["items"]) == {"old", "new"}
    assert saved["next_page"] == 30
