from src.novice_navigation import (
    build_best_available_view,
    build_ending_soon_view,
    build_watch_view,
    build_research_view,
)

def test_best_available_exposes_safe_market_value():
    row={
        "titel":"Kort A","beslut":"SKIP","expected_resale":250,
        "valuation_display_safe":True,"deal_score":10
    }
    out=build_best_available_view([row])
    assert out["rows"][0]["market_value"] == 250

def test_best_available_hides_unsafe_market_value():
    row={
        "titel":"Kort B","beslut":"SKIP","expected_resale":250,
        "valuation_display_safe":False,"deal_score":10
    }
    out=build_best_available_view([row])
    assert out["rows"][0]["market_value"] is None

def test_watch_exposes_market_value():
    row={
        "titel":"Kort C","beslut":"KANSKE","expected_resale":175,
        "valuation_display_safe":True
    }
    out=build_watch_view([row])
    assert out["rows"][0]["market_value"] == 175

def test_research_exposes_market_value_without_creating_buy():
    row={
        "titel":"Kort D","beslut":"SKIP","expected_resale":300,
        "valuation_display_safe":True,"is_hidden_find_candidate":True
    }
    out=build_research_view([row])
    assert out["rows"][0]["market_value"] == 300
    assert out["rows"][0]["decision"] == "SKIP"
