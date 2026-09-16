from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

import pytest

import fetch_tradera_pages as cli
from src import tradera_fetcher as fetcher
from src.latest_market import LATEST_MAX_PAGES, latest_analysis_items, newest_first_url
from src.search_run_cache import build_search_run_signature


def test_newest_sort_preserves_filters_and_has_one_sort_parameter():
    url = newest_first_url("https://www.tradera.com/category/293316?sortBy=Relevance&q=Young+Guns&page=2")
    params = parse_qs(urlsplit(url).query)
    assert params == {"sortBy": ["AddedOn"], "q": ["Young Guns"], "page": ["2"]}
    assert newest_first_url(url) == url


def test_latest_snapshot_is_selected_per_sport_with_legacy_fallback():
    def row(category, scan=None):
        return {"source_category": category, **({"discovery_sort": "AddedOn", "latest_scan_at": scan} if scan else {})}
    old_h, first_h, latest_h = row("Hockey - NHL"), row("Hockey - NHL", "2026-09-15"), row("Hockey - NHL", "2026-09-16")
    old_f, latest_f = row("Fotboll"), row("Fotboll", "2026-09-14")
    assert latest_analysis_items([old_h, first_h, latest_h, old_f]) == [latest_h, old_f]
    assert latest_analysis_items([old_h, first_h, latest_h, old_f, latest_f]) == [latest_h, latest_f]
    assert latest_analysis_items([old_h, old_f]) == [old_h, old_f]
    assert latest_analysis_items([]) == []


def test_older_refresh_preserves_latest_membership_and_enriched_details():
    old = {"lank": "https://example/1", "pris": 20, "frakt": 22, "full_description": "Extra",
           "discovery_sort": "AddedOn", "latest_scan_at": "2026-09-16"}
    merged = fetcher.merge_items([old, {"lank": "https://example/archive"}],
                                [{"lank": old["lank"], "pris": 10, "frakt": None}])
    assert len(merged) == 2
    assert merged[0]["pris"] == 10
    assert merged[0]["frakt"] == 22
    assert merged[0]["full_description"] == "Extra"
    assert merged[0]["latest_scan_at"] == old["latest_scan_at"]


def test_latest_cli_is_bounded_and_preserves_archive(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher, "STATE_PATH", tmp_path / "state.json")
    output = tmp_path / "data.json"
    old = {"lank": "https://example/old", "source_category": "Hockey - NHL", "pris": 50}
    fetcher.save_items([old], output)

    def fake_fetch(**kwargs):
        assert kwargs["newest_first"] is True
        assert kwargs["smart_max_pages"] == LATEST_MAX_PAGES == 3
        assert kwargs["detail_limit"] == 0
        assert kwargs["known_links"] == {old["lank"]}
        assert kwargs["stop_after_known_pages"] == 2
        assert kwargs["start_page"] == 1
        new = {"lank": "https://example/new", "source_category": "Hockey - NHL", "pris": 10}
        kwargs["page_callback"](page_items=[new], page_number=1, pages_scanned=1, items_seen=1, new_items=1)
        assert len(fetcher.load_items(output)) == 2
        return [new], []

    monkeypatch.setattr(cli, "fetch_tradera_category", fake_fetch)
    assert cli.fetch_one_category("Hockey - NHL", "latest", False, output, 250) == (1, 1, 2)
    assert {x["lank"] for x in fetcher.load_items(output)} == {old["lank"], "https://example/new"}


@pytest.mark.parametrize("known,expected_pages", [(False, 3), (True, 2)])
def test_real_crawler_latest_sort_bound_and_known_stop(tmp_path, monkeypatch, known, expected_pages):
    import playwright.sync_api
    monkeypatch.setattr(fetcher, "STATE_PATH", tmp_path / "state.json")
    urls = []

    class Page:
        def goto(self, url, **kwargs):
            urls.append(url)
        def wait_for_timeout(self, duration):
            pass
        def locator(self, selector):
            return SimpleNamespace(count=lambda: 1, nth=lambda index: len(urls))

    browser = SimpleNamespace(new_page=lambda **kwargs: Page(), close=lambda: None)
    manager = Mock()
    manager.__enter__ = Mock(return_value=object())
    manager.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(playwright.sync_api, "sync_playwright", lambda: manager)
    monkeypatch.setattr(fetcher, "_launch_chromium", lambda *args, **kwargs: browser)
    monkeypatch.setattr(fetcher.time, "sleep", lambda _: None)
    monkeypatch.setattr(fetcher, "extract_item", lambda anchor, category, page: {
        "lank": f"https://www.tradera.com/item/293316/{page}/card", "source_category": category, "sida": page,
    })
    checkpoint = Mock()
    enrich = Mock(side_effect=AssertionError("latest mode must not open detail pages"))
    monkeypatch.setattr(fetcher, "mark_page_loaded", checkpoint)
    monkeypatch.setattr(fetcher, "enrich_selected_listings", enrich)
    saved = []
    items, _ = fetcher.fetch_tradera_category(
        "Hockey - NHL", newest_first=True, detail_limit=0, smart_max_pages=3,
        known_links={f"https://www.tradera.com/item/293316/{p}/card" for p in range(1, 4)} if known else set(),
        page_callback=lambda **kwargs: saved.extend(kwargs["page_items"]),
    )
    assert len(urls) == len(items) == len(saved) == expected_pages
    assert all(parse_qs(urlsplit(url).query)["sortBy"] == ["AddedOn"] for url in urls)
    assert {item["discovery_sort"] for item in items} == {"AddedOn"}
    assert len({item["latest_scan_at"] for item in items}) == 1
    checkpoint.assert_not_called()
    enrich.assert_not_called()


def test_latest_scan_cannot_reset_legacy_coverage(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher, "STATE_PATH", tmp_path / "state.json")
    fetcher.mark_page_loaded("Hockey - NHL", 70)
    before = fetcher.load_fetch_state()
    fetcher.reconcile_market_state_with_items([{
        "lank": "https://www.tradera.com/item/293316/123/card",
        "sida": 1, "discovery_sort": "AddedOn",
    }])
    assert fetcher.load_fetch_state() == before


def test_cache_separates_recent_and_archive_search():
    args = dict(data_version="1", app_version="test", sport="hockey", search="", max_price=100,
                sale_type="Alla", strategy="premium_flip", numbered_only=False, patch_only=False, auto_only=False)
    assert build_search_run_signature(**args) != build_search_run_signature(**args, include_older=True)


def test_app_has_one_latest_action_and_no_duplicate_admin_actions():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
    assert not app.exception
    primary = app.button(key="top_fetch_selected")
    assert "senaste annonser" in primary.label
    labels = [button.label for button in app.button]
    assert "Uppdatera alla sporter" not in labels
    assert "Endast vald sport" not in labels
    assert labels.count("Kör vald hämtning") == 1
    assert len(app.radio(key="onboarding_fetch_scope").options) == 3
    archive = next(x for x in app.checkbox if x.label == "Ta med äldre sparade annonser")
    assert archive.value is False
