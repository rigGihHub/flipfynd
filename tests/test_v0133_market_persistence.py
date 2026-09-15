from pathlib import Path


def test_app_restores_active_market_and_passes_database_to_fetcher():
    app = Path("app.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "v0.14.10"' in app
    assert 'load_namespace(DATABASE_URL, "active_market", [])' in app
    assert '"FLIPFYND_DATABASE_URL": DATABASE_URL' in app


def test_fetcher_persists_the_canonical_active_market():
    source = Path("src/tradera_fetcher.py").read_text(encoding="utf-8")
    assert 'save_namespace(database_url, "active_market", list(items or []))' in source
    assert "path.resolve() == DATA_PATH.resolve()" in source
