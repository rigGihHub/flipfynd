from src.sold_acquisition_strategy import build_sold_acquisition_strategy


def test_direct_realized_sources_rank_ahead_of_price_guides():
    out=build_sold_acquisition_strategy(limit=20)
    rows=out["rows"]
    direct=[r for r in rows if r["evidence_type"]=="DIRECT_REALIZED_SALES"]
    guides=[r for r in rows if r["evidence_type"]=="AGGREGATED_PRICE_GUIDE"]
    assert direct
    assert guides
    assert min(r["priority_score"] for r in direct) > max(r["priority_score"] for r in guides)


def test_strategy_does_not_claim_automation_when_registry_has_none():
    out=build_sold_acquisition_strategy()
    assert out["automated_source_count"]==0
    assert out["status"]=="HUMAN_VERIFIED_ACQUISITION_REQUIRED"
    assert all(r["can_create_exact_sold_automatically"] is False for r in out["rows"])


def test_tradera_explicit_import_is_high_priority():
    out=build_sold_acquisition_strategy(limit=20)
    tradera=next(r for r in out["rows"] if r["key"]=="tradera_sold")
    assert tradera["status"]=="RESEARCH_AND_EXPLICIT_IMPORT"
    assert "explicit" in tradera["next_action"].casefold()
