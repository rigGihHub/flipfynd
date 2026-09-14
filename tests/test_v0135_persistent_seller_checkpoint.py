from src import seller_checkpoint_store as store


def test_checkpoint_uses_database_when_runtime_and_session_are_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "_ROOT", tmp_path)
    saved = {}
    monkeypatch.setattr("src.persistent_store.save_namespace", lambda url, namespace, payload: saved.__setitem__(namespace, payload))
    monkeypatch.setattr("src.persistent_store.load_namespace", lambda url, namespace, default: saved.get(namespace, default))

    checkpoint = {"next_page": 4, "pages_read": 3, "items": {"1": {"titel": "Kort"}}}
    store.save_checkpoint("etanol71", checkpoint, database_url="postgresql://test")
    store._path("etanol71").unlink()

    restored = store.load_checkpoint("etanol71", database_url="postgresql://test")
    assert restored["next_page"] == 4
    assert restored["pages_read"] == 3


def test_cleared_database_checkpoint_is_not_restored(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "_ROOT", tmp_path)
    saved = {}
    monkeypatch.setattr("src.persistent_store.save_namespace", lambda url, namespace, payload: saved.__setitem__(namespace, payload))
    monkeypatch.setattr("src.persistent_store.load_namespace", lambda url, namespace, default: saved.get(namespace, default))

    store.save_checkpoint("seller", {"next_page": 9}, database_url="postgresql://test")
    store.clear_checkpoint("seller", database_url="postgresql://test")
    assert store.load_checkpoint("seller", database_url="postgresql://test") is None


def test_app_passes_visible_result_checkpoint_back_to_controller():
    app = __import__("pathlib").Path("app.py").read_text(encoding="utf-8")
    assert app.count('resume_checkpoint=_seller_previous_result.get("public_checkpoint")') == 2
    assert '_seller_display_rows = (_find_rows + _research_rows + _weak_rows)[:5]' in app
