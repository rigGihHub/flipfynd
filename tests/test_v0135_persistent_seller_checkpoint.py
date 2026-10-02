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
    assert "resume_checkpoint=_visible_cp" in app
    assert 'resume_checkpoint=_seller_previous_result.get("public_checkpoint")' in app


def test_furthest_checkpoint_wins_even_if_session_is_stale(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "_ROOT", tmp_path)
    saved = {}
    monkeypatch.setattr("src.persistent_store.save_namespace", lambda url, namespace, payload: saved.__setitem__(namespace, payload))
    monkeypatch.setattr("src.persistent_store.load_namespace", lambda url, namespace, default: saved.get(namespace, default))
    session = {}
    durable = {"next_page": 29, "pages_read": 28, "items": {str(i): {} for i in range(2160)}}
    store.save_checkpoint("big-seller", durable, database_url="postgresql://test")
    session["big-seller"] = {"next_page": 10, "pages_read": 9, "items": {str(i): {} for i in range(720)}}
    restored = store.load_checkpoint("big-seller", session=session, database_url="postgresql://test")
    assert restored["next_page"] == 29
    assert len(restored["items"]) == 2160


def test_stale_save_cannot_rewind_durable_checkpoint(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "_ROOT", tmp_path)
    saved = {}
    monkeypatch.setattr("src.persistent_store.save_namespace", lambda url, namespace, payload: saved.__setitem__(namespace, payload))
    monkeypatch.setattr("src.persistent_store.load_namespace", lambda url, namespace, default: saved.get(namespace, default))
    store.save_checkpoint("seller", {"next_page": 29, "pages_read": 28, "items": {"new": {}}}, database_url="postgresql://test")
    store.save_checkpoint("seller", {"next_page": 10, "pages_read": 9, "items": {"old": {}}}, database_url="postgresql://test")
    restored = store.load_checkpoint("seller", database_url="postgresql://test")
    assert restored["next_page"] == 29
    assert "new" in restored["items"]


def test_removed_candidate_survives_stale_and_more_advanced_worker_checkpoints(monkeypatch, tmp_path):
    from src.seller_analysis_registry import begin_run
    monkeypatch.setattr(store, '_ROOT', tmp_path)
    registry = begin_run(None)
    checkpoint = {'next_page': 4, 'pages_read': 3, 'items': {'1': {}},
                  'analysis_registry': registry}
    session = {}
    store.save_checkpoint('hidden-test', checkpoint, session=session)
    removed_registry = dict(registry, dismissed_keys=['1'])
    removed = dict(checkpoint, analysis_registry=removed_registry)
    store.save_checkpoint('hidden-test', removed, session=session)
    # The older snapshot must not resurrect the card, even with a newer page cursor.
    store.save_checkpoint('hidden-test', dict(checkpoint, next_page=7, pages_read=6), session=session)
    restored = store.load_checkpoint('hidden-test', session=session)
    assert restored['next_page'] == 7
    assert restored['analysis_registry']['dismissed_keys'] == ['1']
    assert store.load_checkpoint('hidden-test')['analysis_registry']['dismissed_keys'] == ['1']
