"""Durable monotonic checkpoint store for Seller Top 5 inventory."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path('/tmp/flipfynd_seller_checkpoints')


def _path(key: str) -> Path:
    digest = hashlib.sha256(str(key or '').encode('utf-8')).hexdigest()
    return _ROOT / f'{digest}.json'


def _namespace(key: str) -> str:
    digest = hashlib.sha256(str(key or '').encode('utf-8')).hexdigest()
    return f'seller_checkpoint::{digest}'


def _progress(value: dict | None) -> tuple[int, int, int]:
    if not isinstance(value, dict):
        return (0, 0, 0)
    items = value.get("items") or {}
    return (
        max(1, int(value.get("next_page") or 1)),
        len(items) if isinstance(items, dict) else 0,
        max(0, int(value.get("pages_read") or 0)),
    )


def furthest_checkpoint(*values) -> dict | None:
    candidates = [dict(v) for v in values if isinstance(v, dict)]
    return max(candidates, key=_progress) if candidates else None


def load_checkpoint(key: str, *, session=None, database_url=None) -> dict | None:
    durable = session_value = local_value = None
    if database_url:
        try:
            from src.persistent_store import load_namespace
            value = load_namespace(database_url, _namespace(key), None)
            if isinstance(value, dict):
                durable = dict(value)
        except Exception:
            pass
    if session is not None:
        try:
            value = session.get(key)
            if isinstance(value, dict):
                session_value = dict(value)
        except Exception:
            pass
    try:
        path = _path(key)
        if path.exists():
            value = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(value, dict):
                local_value = dict(value)
    except Exception:
        pass
    chosen = furthest_checkpoint(durable, session_value, local_value)
    if chosen is not None and session is not None:
        try:
            session[key] = chosen
        except Exception:
            pass
    return chosen


def save_checkpoint(key: str, value: dict, *, session=None, database_url=None) -> None:
    incoming = dict(value or {})
    existing = load_checkpoint(key, session=session, database_url=database_url)
    payload = furthest_checkpoint(existing, incoming) or incoming
    payload["checkpoint_saved_at"] = datetime.now(timezone.utc).isoformat()
    if session is not None:
        try:
            session[key] = payload
        except Exception:
            pass
    try:
        _ROOT.mkdir(parents=True, exist_ok=True)
        path = _path(key)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        tmp.replace(path)
    except Exception:
        pass
    if database_url:
        try:
            from src.persistent_store import save_namespace
            save_namespace(database_url, _namespace(key), payload)
        except Exception:
            pass


def clear_checkpoint(key: str, *, session=None, database_url=None) -> None:
    if session is not None:
        try:
            if key in session:
                del session[key]
        except Exception:
            pass
    try:
        _path(key).unlink(missing_ok=True)
    except Exception:
        pass
    if database_url:
        try:
            from src.persistent_store import save_namespace
            save_namespace(database_url, _namespace(key), None)
        except Exception:
            pass
