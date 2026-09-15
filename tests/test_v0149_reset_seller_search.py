from src import seller_top5_controller as controller


def test_reset_clears_exact_checkpoint_from_all_storage_layers(monkeypatch):
    cleared = {}
    session = {}
    monkeypatch.setattr(
        controller,
        "clear_checkpoint",
        lambda key, session=None, database_url=None: cleared.update(
            key=key, session=session, database_url=database_url
        ),
    )
    key = controller.reset_seller_top5_search(
        "Etanol71",
        "https://www.tradera.com/profile/items/5412219/etanol71",
        database_url="postgresql://test",
        session=session,
    )
    assert key == cleared["key"]
    assert "etanol71" in key
    assert cleared["session"] is session
    assert cleared["database_url"] == "postgresql://test"


def test_app_has_visible_reset_without_touching_ordinary_results():
    from pathlib import Path

    app = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert '"Rensa säljsökningen"' in app
    callback = app[app.index("def _clear_seller_top5_ui"):app.index("with st.sidebar.expander", app.index("def _clear_seller_top5_ui"))]
    assert 'reset_seller_top5_search(' in callback
    assert 'seller_top5_result' in callback
    assert 'seller_top5_alias' in callback
    assert 'seller_top5_profile_url' in callback
    assert 'st.session_state["results"]' not in callback
