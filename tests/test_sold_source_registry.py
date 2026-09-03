from src.sold_source_registry import sold_source_registry, source_readiness_summary


def test_registry_never_claims_automatic_ingestion_without_connector():
    sources = sold_source_registry()
    assert sources
    assert all(source["supports_sports_cards"] for source in sources)
    assert all(source["research_url"].startswith("https://") for source in sources)
    assert all(source["automated_ingestion"] is False for source in sources)


def test_readiness_is_transparent_when_no_external_connector_exists():
    summary = source_readiness_summary()
    assert summary["automated_count"] == 0
    assert summary["research_only_count"] == summary["source_count"]
    assert summary["status"] == "MANUAL_RESEARCH_REQUIRED"
