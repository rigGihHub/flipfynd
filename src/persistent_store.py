"""Durable JSON namespace storage for FlipFynd.

The app can use a PostgreSQL database (for example Neon) when a database URL
is configured. Without one, callers may fall back to the existing local JSON
files. This module deliberately stores opaque JSON payloads; domain validation
continues to live in the journal and sold-comp modules.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

TABLE_NAME = "flipfynd_state"


@dataclass(frozen=True)
class StorageStatus:
    backend: str
    durable: bool
    configured: bool
    detail: str


def _import_psycopg():
    try:
        import psycopg  # type: ignore
    except ImportError as exc:  # pragma: no cover - guarded in app/deploy
        raise RuntimeError("psycopg saknas; installera psycopg[binary] för PostgreSQL-lagring") from exc
    return psycopg


def storage_status(database_url: Optional[str]) -> StorageStatus:
    if database_url:
        return StorageStatus(
            backend="PostgreSQL",
            durable=True,
            configured=True,
            detail="Persistent databas är konfigurerad.",
        )
    return StorageStatus(
        backend="Lokal runtime",
        durable=False,
        configured=False,
        detail="Ingen persistent databas är konfigurerad; lokala JSON-filer används.",
    )




def probe_database(database_url: Optional[str]) -> StorageStatus:
    """Verify that the configured PostgreSQL backend is actually reachable.

    This performs a lightweight read-only SELECT 1. A configured URL is not
    treated as healthy until the connection succeeds.
    """
    if not database_url:
        return storage_status(None)
    try:
        psycopg = _import_psycopg()
        with psycopg.connect(database_url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                row = cur.fetchone()
        if not row or row[0] != 1:
            raise RuntimeError("Databasen svarade inte som förväntat.")
        return StorageStatus(
            backend="PostgreSQL",
            durable=True,
            configured=True,
            detail="Persistent databas är konfigurerad och nåbar.",
        )
    except Exception as exc:
        return StorageStatus(
            backend="PostgreSQL",
            durable=False,
            configured=True,
            detail=f"Persistent databas är konfigurerad men kunde inte nås: {exc}",
        )


def namespace_status(database_url: str) -> list[dict[str, Any]]:
    """Return lightweight metadata for FlipFynd namespaces without exposing payloads."""
    ensure_schema(database_url)
    psycopg = _import_psycopg()
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT namespace, jsonb_typeof(payload), updated_at FROM {TABLE_NAME} ORDER BY namespace"
            )
            rows = cur.fetchall()
    return [
        {"namespace": row[0], "payload_type": row[1], "updated_at": row[2]}
        for row in rows
    ]

def ensure_schema(database_url: str) -> None:
    psycopg = _import_psycopg()
    with psycopg.connect(database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    namespace TEXT PRIMARY KEY,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )


def load_namespace(database_url: str, namespace: str, default: Any) -> Any:
    ensure_schema(database_url)
    psycopg = _import_psycopg()
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT payload FROM {TABLE_NAME} WHERE namespace = %s",
                (namespace,),
            )
            row = cur.fetchone()
    if not row:
        return default
    payload = row[0]
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return default
    return payload


def save_namespace(database_url: str, namespace: str, payload: Any) -> None:
    ensure_schema(database_url)
    psycopg = _import_psycopg()
    encoded = json.dumps(payload, ensure_ascii=False)
    with psycopg.connect(database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {TABLE_NAME} (namespace, payload, updated_at)
                VALUES (%s, %s::jsonb, NOW())
                ON CONFLICT (namespace)
                DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()
                """,
                (namespace, encoded),
            )


def migrate_namespace_if_empty(database_url: str, namespace: str, payload: Any) -> bool:
    """Seed a namespace once when the database has no value yet.

    Returns True only when data was written. Existing persistent data is never
    overwritten by a local runtime copy.
    """
    current = load_namespace(database_url, namespace, None)
    if current is not None:
        return False
    save_namespace(database_url, namespace, payload)
    return True
