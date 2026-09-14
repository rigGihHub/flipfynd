from src.sold_source_registry import access_blocked_sources, sold_source_registry, source_readiness_summary


def test_marketplace_insights_is_visible_but_not_claimed_as_ready():
    by_key = {row["key"]: row for row in sold_source_registry()}
    source = by_key["ebay_marketplace_insights"]
    assert source["evidence_type"] == "DIRECT_REALIZED_SALES"
    assert source["automated_ingestion"] is False
    assert source["status"] == "DIRECT_API_ACCESS_BLOCKED"


def test_tradera_does_not_claim_general_market_sold_feed():
    by_key = {row["key"]: row for row in sold_source_registry()}
    assert by_key["tradera_sold"]["access_requirement"] == "GENERAL_MARKET_SOLD_FEED_NOT_AVAILABLE"


def test_readiness_reports_blocked_direct_api_separately():
    summary = source_readiness_summary()
    assert summary["automated_count"] == 0
    assert summary["access_blocked_count"] >= 1
    assert access_blocked_sources()
