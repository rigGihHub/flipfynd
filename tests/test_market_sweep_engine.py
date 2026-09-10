from src.market_sweep_engine import (
    build_market_sweep_map,
    market_sweep_tags,
    select_market_sweep_indices,
)

def test_map_creates_no_value_score_or_decision():
    out=build_market_sweep_map([])
    assert out["creates_new_score"] is False
    assert out["creates_new_decision"] is False
    assert out["creates_new_value"] is False

def test_cheap_quarter_is_relative_to_current_pool():
    candidates=[
        ({"pris":10},{},{}),
        ({"pris":20},{},{}),
        ({"pris":100},{},{}),
        ({"pris":200},{},{}),
    ]
    out=build_market_sweep_map(candidates)
    assert out["low_price_cutoff"] == 10.0
    assert "cheap-quarter" in out["rows"][0]["tags"]
    assert "cheap-quarter" not in out["rows"][-1]["tags"]

def test_newest_pages_is_page_based_not_time_claim():
    tags=market_sweep_tags({"pris":50,"sida":2},{},{},low_price_cutoff=10)
    assert "newest-pages" in tags

def test_bad_listing_and_lot_routes_reuse_existing_signals():
    fast={
        "listing_quality_score":40,
        "listing_quality_warnings":["kortnummer saknas","set/program saknas eller är otydligt"],
        "is_lot":True,
        "is_hidden_find_candidate":True,
        "hidden_find_reasons":["kort eller generisk rubrik"],
    }
    tags=market_sweep_tags({"pris":100},fast,{},low_price_cutoff=10)
    assert "bad-listing" in tags
    assert "lot" in tags
    assert "lot-treasure" in tags

def test_search_expansion_candidates_get_own_route():
    tags=market_sweep_tags(
        {"pris":100,"source_type":"tradera_api_search_expansion"},
        {},{},low_price_cutoff=10)
    assert "search-expansion" in tags

def test_selector_prefers_distinct_omitted_routes_and_respects_cap():
    candidates=[
        ({"pris":100,"sida":5},{"rank_score":100,"player_name":"A"},{}),
        ({"pris":5,"sida":9},{"rank_score":20,"player_name":"B"},{}),
        ({"pris":100,"sida":1},{"rank_score":10,"player_name":"C"},{}),
        ({"pris":100},{"rank_score":8,"player_name":"D","rookie_importance_matched":True},{}),
    ]
    chosen=select_market_sweep_indices(candidates,[0],extra_limit=2,total_hard_cap=3)
    assert len(chosen)==2
    assert set(chosen).issubset({1,2,3})
