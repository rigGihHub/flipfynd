"""Compact per-browser result backup; never a shared marketplace cache."""
import base64
import json
from pathlib import Path
import zlib

MAX_COMPRESSED = 3_000_000
MAX_JSON = 32_000_000


def encode_snapshot(token, snapshot):
    from src.resumable_search import valid_token
    if not valid_token(token) or not isinstance(snapshot, dict):
        return ""
    raw = json.dumps({"token": token, "snapshot": snapshot}, ensure_ascii=False, default=str).encode()
    if len(raw) > MAX_JSON:
        return ""
    blob = base64.b64encode(zlib.compress(raw, 6)).decode()
    return blob if len(blob) <= MAX_COMPRESSED else ""


def decode_snapshot(token, blob):
    from src.resumable_search import valid_token
    if not valid_token(token) or not isinstance(blob, str) or len(blob) > MAX_COMPRESSED:
        return None
    try:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(base64.b64decode(blob, validate=True), MAX_JSON + 1)
        if len(raw) > MAX_JSON or not decoder.eof or decoder.unused_data:
            return None
        data = json.loads(raw)
        snapshot = data.get("snapshot")
        if data.get("token") != token or not isinstance(snapshot, dict):
            return None
        if snapshot.get("status") not in {"RUNNING", "COMPLETED", "FAILED", "INTERRUPTED"}:
            return None
        if not isinstance(snapshot.get("params"), dict):
            return None
        widgets = snapshot["params"].get("widgets") or {}
        allowed = {"search_sport", "search_budget", "search_text", "search_archive", "search_sale_type", "ordinary_card_type_filter"}
        snapshot["params"]["widgets"] = {key: value for key, value in widgets.items() if key in allowed}
        if snapshot["status"] == "COMPLETED" and (not isinstance(snapshot.get("results"), list)
                or not isinstance(snapshot.get("debug"), dict)
                or any(not isinstance(row, dict) for row in snapshot["results"])):
            return None
        if snapshot["status"] == "RUNNING":
            snapshot["status"] = "INTERRUPTED"
        return snapshot
    except (ValueError, TypeError, zlib.error, AttributeError):
        return None


def browser_backup(token, snapshot, *, clear=False):
    import streamlit as st
    from streamlit.components.v1 import declare_component
    component = declare_component("flipfynd_search_backup", path=str(Path(__file__).with_name("search_browser_storage")))
    identity = (token, (snapshot or {}).get("status"), (snapshot or {}).get("completed_at"))
    if st.session_state.get("_browser_backup_identity") != identity:
        st.session_state["_browser_backup_identity"] = identity
        st.session_state["_browser_backup_blob"] = encode_snapshot(token, snapshot)
    return component(token=token, blob=st.session_state.get("_browser_backup_blob", ""),
                     clear=clear, key="browser_search_backup", default=None)


def recover_browser_search(token, blob, database_url=None):
    from src import resumable_search
    snapshot = decode_snapshot(token, blob)
    if snapshot is None:
        return False
    # A live server job wins over the browser copy, but its token still has
    # to be put back into the URL when returning to the app's base address.
    resumable_search.restore_browser_snapshot(token, snapshot, database_url)
    return resumable_search.load(token, database_url) is not None
