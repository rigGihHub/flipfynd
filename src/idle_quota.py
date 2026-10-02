"""Nonblocking quota metadata for the idle page; no search is started."""
from concurrent.futures import ThreadPoolExecutor
from threading import RLock
import time

_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix='quota-metadata')
_LOCK = RLock()
_TASKS = {}


def request(key, fetch, *, now=None):
    """Return last completed metadata immediately, single-flight per account."""
    now = time.monotonic() if now is None else now
    with _LOCK:
        entry = _TASKS.get(key)
        if entry and entry['future'].done():
            try:
                entry['value'] = entry['future'].result()
            except Exception:
                entry['value'] = {'status': 'QUOTA_CHECK_FAILED'}
        value = (entry or {}).get('value')
        if not entry or (entry['future'].done() and now - entry['started'] >= 60):
            entry = {'future': _POOL.submit(fetch), 'started': now, 'value': value}
            _TASKS[key] = entry
        return dict(entry.get('value') or {}), not entry['future'].done()


def render_counter(credentials, *, searching=False):
    import streamlit as st
    from src import ebay_browse_context as ebay, ebay_quota as quota
    from src.ebay_quota_ui import render_quota_counter
    key = ebay._limit_key(*credentials)

    @st.fragment(run_every='2s')
    def panel():
        current = quota.quota_status(key)
        pending = False
        if not searching and all(credentials):
            fetched, pending = request(key, lambda: ebay.fetch_configured_quota(credentials=credentials))
            if fetched.get('last_check', 0) > current.get('last_check', 0) or not current:
                current = fetched
        st.session_state['ebay_live_quota'] = current
        render_quota_counter(current)
        if pending:
            st.caption('Kontrollerar antal eBay-anrop i bakgrunden. Du kan använda appen under tiden.')
        st.button('↻ Uppdatera antal anrop', key='refresh_ebay_counter', disabled=searching,
                  help='Kvoten uppdateras i bakgrunden, högst en gång per minut.')
    panel()
