from src.search_run_cache import build_search_run_signature, get_reusable_search, store_reusable_search


def _signature(**updates):
    values = {
        "data_version": "market-1", "app_version": "v0.14.3",
        "sport": "football", "search": " Bukayo   SAKA ", "max_price": 500,
        "sale_type": "Alla", "strategy": "quick_flip", "numbered_only": False,
        "patch_only": False, "auto_only": False,
    }
    values.update(updates)
    return build_search_run_signature(**values)


def test_equivalent_search_text_reuses_completed_run():
    assert _signature() == _signature(search="bukayo saka")


def test_market_analysis_or_filter_change_invalidates_run():
    baseline = _signature()
    assert baseline != _signature(data_version="market-2")
    assert baseline != _signature(app_version="v0.14.4")
    assert baseline != _signature(max_price=501)
    assert baseline != _signature(auto_only=True)


def test_cache_accepts_only_complete_results_and_stays_bounded():
    signature = _signature()
    cache = store_reusable_search(signature, [{"titel": "Kort"}], {"final_results": 1})
    assert list(cache) == [signature]
    assert get_reusable_search(cache, signature) == ([{"titel": "Kort"}], {"final_results": 1})
    assert get_reusable_search({signature: {"results": "bad", "debug": {}}}, signature) is None
