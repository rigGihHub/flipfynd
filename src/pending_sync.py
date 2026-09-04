"""Local pending-sync guard for persistent FlipFynd state.

When PostgreSQL is configured but temporarily unavailable, FlipFynd can keep the
latest write as a local pending snapshot. The snapshot is deliberately explicit:
it is never silently merged with database data. The app can later retry the
whole namespace snapshot and clear it only after a successful database write.

This queue is still runtime-local and therefore not a substitute for PostgreSQL.
Its purpose is to prevent silent divergence during a temporary database outage.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


def _empty_state() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "pending": {}}


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def payload_fingerprint(payload: Any) -> str:
    """Stable short SHA-256 fingerprint for diagnostics, never for identity."""
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:16]


def load_pending(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return _empty_state()
    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_state()
    if not isinstance(raw, dict):
        return _empty_state()
    pending = raw.get("pending")
    if not isinstance(pending, dict):
        pending = {}
    return {"schema_version": SCHEMA_VERSION, "pending": pending}


def _save_state(path: str | Path, state: dict[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(file_path)


def record_pending(
    path: str | Path,
    namespace: str,
    payload: Any,
    *,
    error: str | None = None,
) -> dict[str, Any]:
    """Store the latest complete namespace snapshot awaiting database sync."""
    if not namespace:
        raise ValueError("namespace krävs")
    state = load_pending(path)
    entry = {
        "namespace": namespace,
        "payload": payload,
        "fingerprint": payload_fingerprint(payload),
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "last_error": str(error)[:500] if error else None,
    }
    state["pending"][namespace] = entry
    _save_state(path, state)
    return entry


def get_pending(path: str | Path, namespace: str) -> dict[str, Any] | None:
    entry = load_pending(path).get("pending", {}).get(namespace)
    return entry if isinstance(entry, dict) else None


def clear_pending(path: str | Path, namespace: str) -> bool:
    state = load_pending(path)
    if namespace not in state["pending"]:
        return False
    del state["pending"][namespace]
    _save_state(path, state)
    return True


def pending_summary(path: str | Path) -> dict[str, Any]:
    pending = load_pending(path).get("pending", {})
    rows = [entry for entry in pending.values() if isinstance(entry, dict)]
    rows.sort(key=lambda row: str(row.get("queued_at") or ""))
    return {
        "count": len(rows),
        "namespaces": [str(row.get("namespace") or "") for row in rows],
        "entries": rows,
    }
