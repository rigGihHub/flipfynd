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
# A Streamlit code reload must not orphan running work or its progress.
_EXECUTOR = globals().get('_EXECUTOR') or ThreadPoolExecutor(max_workers=1, thread_name_prefix='flipfynd-search')
_LOCK = globals().get('_LOCK') or RLock()
_JOBS = globals().get('_JOBS', {})


def valid_token(token):
    return bool(re.fullmatch(r'[a-f0-9]{32}', str(token or '')))


def new_token():
    return uuid.uuid4().hex


def _save(token, payload, database_url=None):
    try:
        _ROOT.mkdir(exist_ok=True)
        path = _ROOT / (token + '.json')
        tmp = path.with_name(token + '.' + uuid.uuid4().hex + '.tmp')
        with tmp.open('w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, default=str)
        tmp.replace(path)
    except OSError:
        pass  # A full/unavailable disk must not abort an otherwise healthy job.
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
        with (_ROOT / (token + '.json')).open(encoding='utf-8') as handle:
            snapshot = json.load(handle)
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


def start(token, params, fn, *, database_url=None, fresh=False):
    if not valid_token(token):
        raise ValueError('Invalid search token')
    with _LOCK:
        existing = load(token, None if fresh else database_url)
        if existing and existing.get('status') in {'RUNNING', 'COMPLETED'}:
            return False
        job = {'status': 'RUNNING', 'params': params, 'started_at': time.time(),
               'progress': {'phase': 'Väntar på att sökningen ska starta', 'requests': 0}}
        _JOBS[token] = job
    _save(token, job)

    def execute():
        from src.search_progress import track_progress
        last_saved = [0.0]
        def progress(payload):
            with _LOCK:
                job['progress'] = payload
                persist = time.monotonic() - last_saved[0] >= 2
                copy = dict(job)
                if persist:
                    last_saved[0] = time.monotonic()
            if persist:
                _save(token, copy)  # Progress must not wait for PostgreSQL.
        try:
            with track_progress(progress):
                results, debug = fn()
            final = {**job, 'status': 'COMPLETED', 'results': results,
                     'debug': debug, 'completed_at': time.time()}
        except Exception as exc:
            final = {**job, 'status': 'FAILED', 'error_type': type(exc).__name__}
        _save(token, final)  # Local recovery is ready before publishing completion.
        with _LOCK:
            _JOBS[token] = final
            # Completed runs remain recoverable on disk. Bound process memory.
            finished = [key for key, value in _JOBS.items() if value['status'] != 'RUNNING']
            for key in finished[:-2]:
                _JOBS.pop(key, None)
        _save(token, final, database_url)  # Never hold the UI job lock during I/O.
    _EXECUTOR.submit(execute)
    return True


def restore_browser_snapshot(token, snapshot, database_url=None):
    """Recover only a validated browser copy when the server has no run."""
    if not valid_token(token) or not isinstance(snapshot, dict):
        return False
    with _LOCK:
        if load(token, database_url) is not None:
            return False
        _JOBS[token] = snapshot
        _save(token, snapshot, database_url)
    return True
