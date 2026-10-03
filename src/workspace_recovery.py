"""Per-browser recovery of UI state. Never serializes processes or credentials."""
from concurrent.futures import ThreadPoolExecutor
import math
import hashlib
import json
from pathlib import Path
from threading import RLock
import time
import uuid

from src.resumable_search import valid_token
from src.persistent_store import load_namespace, save_namespace

INLINE_COMPONENT_DELIVERY = True

_ROOT = Path(__file__).resolve().parent.parent / 'workspace_snapshots'
_LOCK = globals().get('_LOCK') or RLock()
_HASHES = globals().get('_HASHES', {})
_BACKUP_POOL = globals().get('_BACKUP_POOL') or ThreadPoolExecutor(max_workers=2, thread_name_prefix='workspace-backup')
_PENDING = globals().get('_PENDING', {})
_BACKUP_ACTIVE = globals().get('_BACKUP_ACTIVE', set())


def _queue_backup(token, value, database_url):
    # Coalesce changes and keep database latency off the Streamlit thread.
    with _LOCK:
        # save() already owns a detached JSON copy. Keep that copy rather than
        # duplicating the entire workspace again while a search is finishing.
        _PENDING[token] = (database_url, value)
        if token in _BACKUP_ACTIVE:
            return
        _BACKUP_ACTIVE.add(token)
    def flush():
        while True:
            with _LOCK:
                item = _PENDING.pop(token, None)
                if item is None:
                    _BACKUP_ACTIVE.discard(token)
                    return
            try:
                save_namespace(item[0], 'workspace:' + token, item[1])
            except Exception:
                pass  # The synchronous local/browser copies remain available.
    _BACKUP_POOL.submit(flush)
WIDGETS = {'search_sport', 'search_budget', 'search_text', 'search_archive', 'search_sale_type',
           'ordinary_card_type_filter', 'show_advanced_terminal', 'onboarding_fetch_scope',
           'extra_fetch_mode', 'seller_top5_alias', 'seller_top5_profile_url',
           'search_minimum_confidence', 'search_show_count', 'search_show_skip'}
FIELDS = WIDGETS | {'results', 'debug', 'seller_top5_result', '_applied_seller_run',
                   'results_data_version', 'fetch_status', 'fetch_category', 'fetch_last_message',
                   'continue_market_after_latest'}
PREFIXES = ('seller_inventory_result_', 'seller_inventory_quick_result_', 'seller_live_full_')
QUERY = {'search_run', 'seller_run', 'seller', 'seller_profile'}
MAX_BYTES = 32_000_000
ENUMS = {'search_sport': {'Hockey', 'Fotboll'},
         'search_sale_type': {'Alla', 'Endast auktioner', 'Endast Köp nu'},
         'ordinary_card_type_filter': {'Alla kort', 'Endast autograf', 'Endast numrerade', 'Endast patch/relic'}}


def snapshot(state, query):
    values = {k: v for k, v in dict(state).items()
              if k in FIELDS or k.startswith(PREFIXES)}
    # The JSON round trip below already detaches every nested value. A deepcopy
    # before it retained another complete result set during serialization.
    # JSON only: no pickle, connection objects, action buttons or pending clicks.
    values = json.loads(json.dumps(values, ensure_ascii=False, default=lambda _: None))
    return {'schema': 1, 'state': values,
            'query': {k: str(v) for k, v in dict(query).items() if k in QUERY}}


def validate(value):
    if not isinstance(value, dict) or value.get('schema') != 1 or not isinstance(value.get('state'), dict):
        return None
    try:
        if len(json.dumps(value, ensure_ascii=False).encode()) > MAX_BYTES:
            return None
    except (TypeError, ValueError):
        return None
    if not isinstance(value.get('query', {}), dict):
        return None
    return snapshot(value['state'], value.get('query') or {}) | {'updated_at': value.get('updated_at', 0)}


def load(token, database_url=None):
    if not valid_token(token):
        return None
    try:
        value = json.loads((_ROOT / (token + '.json')).read_text())
    except (OSError, ValueError):
        value = None
        if database_url:
            try:
                value = load_namespace(database_url, 'workspace:' + token, None)
            except Exception:
                pass
    return validate(value)


def save(token, value, database_url=None):
    value = validate(value)
    if not valid_token(token) or value is None:
        return False
    payload = json.dumps({k: v for k, v in value.items() if k != 'updated_at'}, ensure_ascii=False)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    with _LOCK:
        if _HASHES.get(token) == digest and (_ROOT / (token + '.json')).exists():
            return True
        value['updated_at'] = time.time()
        path = _ROOT / (token + '.json')
        tmp = path.with_name(token + '.' + uuid.uuid4().hex + '.tmp')
        try:
            _ROOT.mkdir(exist_ok=True)
            tmp.write_text(json.dumps(value, ensure_ascii=False))
            tmp.replace(path)
        except OSError:
            return False
        _HASHES[token] = digest
        for old in list(_HASHES)[:-64]:
            _HASHES.pop(old, None)
    if database_url:
        _queue_backup(token, value, database_url)
    return True


def restore(state, query, value, drafts=None, *, replace=False):
    value = validate(value)
    if not value:
        return
    for key, item in value['state'].items():
        # Restore before widgets are constructed. Existing live values win.
        if replace or key not in state:
            state[key] = item
    for key, item in value['query'].items():
        if key not in query:
            query[key] = item
    try:
        newer = isinstance(drafts, dict) and float(drafts.get('at') or 0) > float(value.get('updated_at') or 0)
    except (TypeError, ValueError):
        newer = False
    if newer and isinstance(drafts.get('widgets'), dict):
        for key, item in drafts['widgets'].items():
            if key in {'search_text', 'seller_top5_alias', 'seller_top5_profile_url'} and isinstance(item, str):
                state[key] = item[:10000]
            elif key == 'search_budget' and type(item) in (int, float) and math.isfinite(item) and 0 <= item <= 10**9:
                state[key] = int(item)
            elif key in ENUMS and isinstance(item, str) and item in ENUMS[key]:
                state[key] = item
            elif key in {'search_archive', 'search_show_skip', 'show_advanced_terminal'} and type(item) is bool:
                state[key] = item
            elif key == 'search_show_count' and type(item) is int and 1 <= item <= 100:
                state[key] = item
            elif key == 'search_minimum_confidence' and type(item) in (int, float) and math.isfinite(item) and 0 <= item <= 1:
                state[key] = float(item)


def persist_current(state, query, database_url=None):
    token = str(query.get('view_run') or '')
    return save(token, snapshot(state, query), database_url)


def recover_ui(state, query, database_url=None):
    """Run before defaults and widgets, including on the plain start URL."""
    from src.browser_search_backup import encode_snapshot, decode_snapshot
    from src.inline_components import mount_inline
    import streamlit as st
    token = str(query.get('view_run') or '')
    requested_token = token
    first = state.get('_workspace_loaded') != token
    # Once hydrated, the live state is authoritative. Re-reading a large
    # snapshot (or retrying its database miss) on every widget change is wasteful.
    current = load(token) if first else snapshot(state, query)
    if current and first:
        restore(state, query, current)
        state['_workspace_loaded'] = token
    if current and state.get('_workspace_browser_loaded') == token:
        persist_current(state, query, database_url)
        current = snapshot(state, query)
    wrapper = {'status': 'COMPLETED', 'params': {}, 'results': [], 'debug': {'workspace': current}}
    blob = encode_snapshot(token, wrapper) if current else ''
    copy = mount_inline('flipfynd_workspace_recovery', 'workspace_browser_storage',
                        data={'token': token if valid_token(token) else '', 'blob': blob,
                              'hydrated': state.get('_workspace_browser_loaded') == token},
                        key='workspace_recovery')
    if not isinstance(copy, dict):
        return
    saved_token = copy.get('token')
    if not valid_token(token):
        token = saved_token if valid_token(saved_token) else uuid.uuid4().hex
        query['view_run'] = token
        # A newly generated token cannot have a remote backup.
        current = load(token) if valid_token(saved_token) else None
        first = True
    if not current and saved_token == token and copy.get('blob'):
        decoded = decode_snapshot(token, copy['blob'])
        recovered = validate((decoded or {}).get('debug', {}).get('workspace'))
        if recovered:
            save(token, recovered, database_url)
            current = recovered
    # Browser/disk recovery usually already has the snapshot. Consult the
    # database only after the handshake, while the loading clock is visible,
    # and never query a token that we just generated.
    if not current and database_url and (saved_token == token or valid_token(requested_token)):
        current = load(token, database_url)
    if state.get('_workspace_browser_loaded') != token:
        restore(state, query, current or snapshot({}, {}), copy.get('drafts'),
                replace=state.get('_workspace_loaded') != token)
        state['_workspace_loaded'] = token
        state['_workspace_browser_loaded'] = token
        persist_current(state, query, database_url)
        # The component response already triggered this run, and all restored
        # values are applied before widgets. A second full rerun adds no value.
