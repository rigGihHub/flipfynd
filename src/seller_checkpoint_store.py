"""Small local checkpoint store for Seller Top 5 public-profile inventory.

The public seller inventory is public data. Checkpoints are written to the app
container as a resilience aid so a dropped Streamlit websocket/session does not
force the user to restart from page 1. Session state is mirrored when available.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

_ROOT = Path('/tmp/flipfynd_seller_checkpoints')


def _path(key: str) -> Path:
    digest = hashlib.sha256(str(key or '').encode('utf-8')).hexdigest()
    return _ROOT / f'{digest}.json'


def _namespace(key: str) -> str:
    digest = hashlib.sha256(str(key or '').encode('utf-8')).hexdigest()
    return f'seller_checkpoint::{digest}'


def load_checkpoint(key: str, *, session=None, database_url=None) -> dict | None:
    # Durable storage is authoritative when configured. A restored browser
    # session may contain an older checkpoint than a previous run already saved
    # to Postgres; reading session state first could then rewind the seller crawl.
    if database_url:
        try:
            from src.persistent_store import load_namespace
            value = load_namespace(database_url, _namespace(key), None)
            if isinstance(value, dict):
                if session is not None:
                    try:
                        session[key] = value
                    except Exception:
                        pass
                return dict(value)
        except Exception:
            pass
    if session is not None:
        try:
            value = session.get(key)
            if isinstance(value, dict):
                return dict(value)
        except Exception:
            pass
    try:
        path = _path(key)
        if path.exists():
            value = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(value, dict):
                if session is not None:
                    try:
                        session[key] = value
                    except Exception:
                        pass
                return value
    except Exception:
        pass
    return None


def save_checkpoint(key: str, value: dict, *, session=None, database_url=None) -> None:
    payload = dict(value or {})
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
