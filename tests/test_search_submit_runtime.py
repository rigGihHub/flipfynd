"""Actual Streamlit submit and new-session recovery without network calls."""
from pathlib import Path
import time
import streamlit as st
from streamlit.testing.v1 import AppTest
from src import loader, resumable_search


def test_search_survives_new_session_with_same_url(monkeypatch, tmp_path):
    st.cache_data.clear()
    monkeypatch.setattr(resumable_search, "_ROOT", tmp_path)
    rows = [{"lank": "https://www.tradera.com/item/293316/1/one",
             "titel": "Connor McDavid Young Guns", "pris": 50000, "frakt": 22,
             "source_category": "Hockey - NHL", "sida": 1}]
    monkeypatch.setattr(loader, "load_data", lambda path: rows if path.endswith("tradera_data.json") else [])
    path = str(Path(__file__).resolve().parents[1] / "app.py")
    app = AppTest.from_file(path, default_timeout=30).run()
    assert not app.exception
    next(b for b in app.button if b.label == "🔎 Hitta fynd").click().run()
    assert not app.exception
    token = app.query_params["search_run"]
    if isinstance(token, list):
        token = token[0]
    for _ in range(100):
        if resumable_search.load(token)["status"] != "RUNNING":
            break
        time.sleep(.02)
    assert resumable_search.load(token)["status"] == "COMPLETED"
    fresh = AppTest.from_file(path, default_timeout=30)
    fresh.query_params["search_run"] = token
    fresh.run()
    assert not fresh.exception, [error.message for error in fresh.exception]
    assert fresh.session_state["debug"]["performance_items"] == 1
    assert fresh.session_state["debug"]["over_budget"] == 1
    assert fresh.session_state["search_budget"] == 1000
    assert fresh.session_state["results"] == []
