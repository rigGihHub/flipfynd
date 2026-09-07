from src.sold_acquisition_pipeline import acquire_sold_batch


def row(**kw):
    base = {"title":"2024-25 Upper Deck Connor Bedard #1", "sold_price":250, "currency":"SEK", "platform":"test", "sold_at":"2026-09-01", "url":"https://example.test/1"}
    base.update(kw)
    return base


def test_routes_verified_sale_without_identity_to_sale_only():
    r=acquire_sold_batch([row()], source_key="feed:test", batch_id="b1")
    assert r["added_count"] == 1
    assert r["route_counts"]["SALE_ONLY"] == 1
    assert r["records"][-1]["intake_status"] == "SALE_ONLY"


def test_exact_ready_requires_explicit_structured_identity():
    r=acquire_sold_batch([row(player_name="Connor Bedard", set_name="Upper Deck", season="2024-25", card_number="1", identity_verified=True, identity_evidence_source="checklist")], batch_id="b2")
    assert r["exact_ready_count"] == 1
    assert r["records"][-1]["exact_identity_ready"] is True


def test_bad_price_goes_to_quarantine():
    r=acquire_sold_batch([row(sold_price="asking only")], batch_id="b3")
    assert r["added_count"] == 0
    assert r["quarantine_count"] == 1


def test_foreign_currency_without_fx_is_quarantined():
    r=acquire_sold_batch([row(currency="USD")], batch_id="b4")
    assert r["quarantine_count"] == 1


def test_duplicate_is_not_added_twice():
    first=acquire_sold_batch([row()], batch_id="b5")
    second=acquire_sold_batch([row()], existing=first["records"], batch_id="b6")
    assert second["added_count"] == 0
    assert second["duplicate_count"] == 1


def test_batch_metadata_is_persisted():
    r=acquire_sold_batch([row()], source_key="export:partner", batch_id="batch-x")
    saved=r["records"][-1]
    assert saved["acquisition_batch_id"] == "batch-x"
    assert saved["acquisition_source"] == "export:partner"
    assert saved["acquisition_pipeline"] == "sold_acquisition_v1"


def test_mixed_batch_keeps_good_rows_and_quarantines_bad_rows():
    r=acquire_sold_batch([row(), {"title":"bad", "sold_price":0}], batch_id="b7")
    assert r["input_count"] == 2
    assert r["accepted_count"] == 1
    assert r["quarantine_count"] == 1
