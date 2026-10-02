"""Track active fetches outside Streamlit sessions; duplicate clicks reuse work."""
from threading import RLock
_LOCK = globals().get('_LOCK') or RLock()
_RUNS = globals().get('_RUNS', {})


def start(key, spawn, *, category, mode):
    with _LOCK:
        current = _RUNS.get(key)
        if current and current['process'].poll() is None:
            return current
        current = {'process': spawn(), 'category': category, 'mode': mode}
        _RUNS[key] = current
        return current


def get(key):
    with _LOCK:
        return _RUNS.get(key)
