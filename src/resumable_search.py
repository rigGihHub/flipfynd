"""Browser-independent jobs and per-search snapshots (no Streamlit calls)."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import RLock
import json
import re
import time
import uuid

from src.persistent_store import load_namespace, save_namespace

_ROOT = Path(__file__).resolve().parent.parent / 'search_snapshots'
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix='flipfynd-search')
_LOCK = RLock()
_JOBS = {}


def valid_token(token):
    return bool(re.fullmatch(r'[a-f0-9]{32}', str(token or '')))


def new_token():
    return uuid.uuid4().hex


def _save(token, payload, database_url=None):
    _ROOT.mkdir(exist_ok=True)
    path = _ROOT / (token + '.json')
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding='utf-8')
    tmp.replace(path)
    if database_url:
        try:
            save_namespace(database_url, 'search:' + token, payload)
        except Exception:
            pass  # Atomic local snapshot still supports session recovery.


def load(token, database_url=None):
    if not valid_token(token):
        return None
    with _LOCK:
        if token in _JOBS:
            return dict(_JOBS[token])
    snapshot = None
    try:
        snapshot = json.loads((_ROOT / (token + '.json')).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        if database_url:
            try:
                snapshot = load_namespace(database_url, 'search:' + token, None)
            except Exception:
                pass
    if isinstance(snapshot, dict) and snapshot.get('status') == 'RUNNING':
        # A process restart interrupted work. Never pretend it is still running.
        snapshot['status'] = 'INTERRUPTED'
    return snapshot if isinstance(snapshot, dict) else None


def start(token, params, fn, *, database_url=None):
    if not valid_token(token):
        raise ValueError('Invalid search token')
    with _LOCK:
        existing = load(token, database_url)
        if existing and existing.get('status') in {'RUNNING', 'COMPLETED'}:
            return False
        job = {'status': 'RUNNING', 'params': params, 'started_at': time.time()}
        _JOBS[token] = job
        _save(token, job, database_url)

    def execute():
        try:
            results, debug = fn()
            final = {**job, 'status': 'COMPLETED', 'results': results,
                     'debug': debug, 'completed_at': time.time()}
        except Exception as exc:
            final = {**job, 'status': 'FAILED', 'error_type': type(exc).__name__}
        with _LOCK:
            _JOBS[token] = final
            _save(token, final, database_url)
            # Completed runs remain recoverable on disk. Bound process memory.
            finished = [key for key, value in _JOBS.items() if value['status'] != 'RUNNING']
            for key in finished[:-8]:
                _JOBS.pop(key, None)
    _EXECUTOR.submit(execute)
    return True
