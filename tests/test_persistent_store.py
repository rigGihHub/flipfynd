import builtins

import pytest

from src.persistent_store import storage_status
import src.persistent_store as persistent_store


def test_storage_status_without_database_is_transparent_runtime_fallback():
    status = storage_status(None)
    assert status.backend == "Lokal runtime"
    assert status.durable is False
    assert status.configured is False


def test_storage_status_with_database_url_is_durable():
    status = storage_status("postgresql://example.invalid/flipfynd")
    assert status.backend == "PostgreSQL"
    assert status.durable is True
    assert status.configured is True


def test_missing_psycopg_has_clear_error(monkeypatch):
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "psycopg":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    with pytest.raises(RuntimeError, match="psycopg"):
        persistent_store._import_psycopg()


def test_probe_database_without_url_is_runtime_fallback():
    status = persistent_store.probe_database(None)
    assert status.configured is False
    assert status.durable is False


def test_probe_database_marks_reachable_postgres_as_verified(monkeypatch):
    class Cursor:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def execute(self, sql):
            assert sql == "SELECT 1"
        def fetchone(self):
            return (1,)

    class Connection:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def cursor(self):
            return Cursor()

    class Psycopg:
        @staticmethod
        def connect(url, connect_timeout=5):
            assert url == "postgresql://configured"
            assert connect_timeout == 5
            return Connection()

    monkeypatch.setattr(persistent_store, "_import_psycopg", lambda: Psycopg)
    status = persistent_store.probe_database("postgresql://configured")
    assert status.configured is True
    assert status.durable is True
    assert "nåbar" in status.detail


def test_probe_database_reports_configured_but_unreachable(monkeypatch):
    class Psycopg:
        @staticmethod
        def connect(*args, **kwargs):
            raise RuntimeError("offline")

    monkeypatch.setattr(persistent_store, "_import_psycopg", lambda: Psycopg)
    status = persistent_store.probe_database("postgresql://configured")
    assert status.configured is True
    assert status.durable is False
    assert "offline" in status.detail
