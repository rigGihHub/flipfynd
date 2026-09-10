from src.search_yield_learning import build_yield_report, route_budget_guidance

def test_non_expansion_ignored():
    assert build_yield_report([{"source_type":"other","beslut":"KÖP"}])["total_hits"]==0

def test_observes_existing_outcomes_only():
    items=[
      {"source_type":"tradera_api_search_expansion","search_expansion_query":"McDavid","search_expansion_order_by":"PriceAscending","search_expansion_kind":"player-exact","beslut":"KÖP","valuation_display_safe":True},
      {"source_type":"tradera_api_search_expansion","search_expansion_query":"McDavid","search_expansion_order_by":"PriceAscending","search_expansion_kind":"player-exact","beslut":"BEVAKA"}]
    out=build_yield_report(items); r=out["rows"][0]
    assert (r["hits"],r["buy"],r["watch"],r["buy_rate_observed"])==(2,1,1,50.0)
    assert out["can_auto_tune"] is False and out["can_change_buy_rules"] is False

def test_small_sample_insufficient():
    report=build_yield_report([{"source_type":"tradera_api_search_expansion","search_expansion_query":"X","search_expansion_order_by":"Relevance","search_expansion_kind":"surname-broad","beslut":"KÖP"}])
    g=route_budget_guidance(report,10)
    assert g["rows"][0]["evidence_status"]=="OTILLRÄCKLIGT_UNDERLAG"
    assert g["changes_execution"] is False and g["changes_buy_logic"] is False
