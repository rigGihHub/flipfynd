from pathlib import Path

def test_app_merges_expansion_candidates_and_has_user_initiated_run():
    app=Path("app.py").read_text(encoding="utf-8")
    assert "SEARCH_EXPANSION_DATA_PATH" in app
    assert 'load_data(str(SEARCH_EXPANSION_DATA_PATH))' in app
    assert "Kör Search Expansion nu" in app
    assert "run_search_plan(" in app
    assert "save_expansion_items(" in app

def test_no_automated_bidding_or_buying_added():
    module=Path("src/tradera_api_search.py").read_text(encoding="utf-8")
    assert "/v4/search" in module
    assert "/buyer/buy" not in module
    assert "bid(" not in module.casefold()
