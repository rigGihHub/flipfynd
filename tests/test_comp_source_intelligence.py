from src.comp_source_intelligence import build_comp_research_plan, exact_identity_query
from src.sold_source_registry import sold_source_registry


def test_exact_identity_query_keeps_variant_and_serial_context():
    q = exact_identity_query({
        "season": "2025-26",
        "set_name": "Upper Deck Series 1",
        "player_name": "Example Player",
        "card_number": "201",
        "parallel": "Outburst Red",
        "serial_denominator": 25,
    })
    assert "Example Player" in q
    assert "#201" in q
    assert "Outburst Red" in q
    assert "/25" in q


def test_comp_plan_prioritizes_realized_sales_over_price_guides():
    plan = build_comp_research_plan({"player_name": "Example Player", "card_number": "201"})
    assert plan["ready"] is True
    assert plan["sources"][0]["key"] == "ebay_product_research"
    assert plan["sources"][1]["key"] == "ebay_sold_search"
    assert plan["sources"][-1]["evidence_class"] == "AGGREGATED_PRICE_GUIDE"
    assert any(s["key"] == "sportscardspro" for s in plan["sources"])


def test_sportscardspro_is_research_only_not_automatic_sold_feed():
    sources = {s["key"]: s for s in sold_source_registry()}
    scp = sources["sportscardspro"]
    assert scp["automated_ingestion"] is False
    assert scp["evidence_type"] == "AGGREGATED_PRICE_GUIDE"
