from types import SimpleNamespace

from src.fetcher_compat import build_fetcher_api


def test_compat_layer_supplies_new_helpers_for_legacy_fetcher():
    legacy = SimpleNamespace(CATEGORY_URLS={"Hockey - NHL": "x"})
    api = build_fetcher_api(legacy)
    assert api.CATEGORY_URLS["Hockey - NHL"] == "x"
    assert api.get_market_sync_status("Hockey - NHL")["next_page"] == 1
    assert api.get_smart_refresh_plan("Hockey - NHL")["due"] is True
    assert api.reconcile_market_state_with_items([]) == []


def test_compat_layer_prefers_real_helpers():
    marker = object()
    def real_sync(category):
        return marker
    legacy = SimpleNamespace(get_market_sync_status=real_sync)
    api = build_fetcher_api(legacy)
    assert api.get_market_sync_status("Fotboll") is marker
