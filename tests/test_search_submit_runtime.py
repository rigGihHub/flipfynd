"""Submit real Streamlit searches, including a module retained across deploys."""
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from src import loader, search_run_cache


@pytest.fixture(autouse=True)
def isolate_streamlit_data_cache():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


@pytest.mark.parametrize("older_cache_module", [False, True])
def test_search_submit_and_scope_switch_work_with_loaded_cache_module(monkeypatch, older_cache_module):
    current_builder = search_run_cache.build_search_run_signature
    if older_cache_module:
        # Exact v0.14.33 call signature: no include_older argument.
        def older_builder(*, data_version, app_version, sport, search,
                          max_price, sale_type, strategy, numbered_only,
                          patch_only, auto_only):
            return current_builder(
                data_version=data_version, app_version=app_version, sport=sport,
                search=search, max_price=max_price, sale_type=sale_type,
                strategy=strategy, numbered_only=numbered_only,
                patch_only=patch_only, auto_only=auto_only,
            )
        monkeypatch.setattr(search_run_cache, "build_search_run_signature", older_builder)

    # Above budget: exercise real selection and completion without network comps.
    rows = [
        {"lank": "https://www.tradera.com/item/293316/1/one",
         "titel": "Connor McDavid Young Guns", "pris": 50000, "frakt": 22,
         "source_category": "Hockey - NHL", "sida": 1,
         "discovery_sort": "AddedOn", "latest_scan_at": "2026-09-16T10:00:00Z"},
        {"lank": "https://www.tradera.com/item/293316/2/two",
         "titel": "Sidney Crosby Young Guns", "pris": 50000, "frakt": 22,
         "source_category": "Hockey - NHL", "sida": 2},
    ]
    monkeypatch.setattr(loader, "load_data", lambda path: rows if path.endswith("tradera_data.json") else [])
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
    assert not app.exception
    next(button for button in app.button if button.label == "🔎 Hitta fynd").click().run()
    assert not app.exception, [error.message for error in app.exception]
    assert app.session_state["debug"]["performance_items"] == 2
    assert app.session_state["debug"]["over_budget"] == 2
    recent_key = next(iter(app.session_state["result_cache"]))
    next(box for box in app.checkbox if box.label == "Ta med äldre sparade annonser").check()
    next(button for button in app.button if button.label == "🔎 Hitta fynd").click().run()
    assert not app.exception, [error.message for error in app.exception]
    assert app.session_state["debug"]["performance_items"] == 2
    assert app.session_state["debug"]["over_budget"] == 2
    assert app.session_state["debug"]["reused_completed_search"] is False
    archive_key = next(iter(app.session_state["result_cache"]))
    assert archive_key != recent_key
    next(button for button in app.button if button.label == "🔎 Hitta fynd").click().run()
    assert not app.exception
    assert app.session_state["debug"]["reused_completed_search"] is True
