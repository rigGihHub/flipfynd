"""Track active fetches outside Streamlit sessions; duplicate clicks reuse work."""
from threading import RLock
_LOCK = globals().get('_LOCK') or RLock()
_RUNS = globals().get('_RUNS', {})


def start(key, spawn, *, category, mode):
    with _LOCK:
        current = _RUNS.get(key)
        if current and current['process'].poll() is None:
            return current
        # Every browser writes the same market file. Concurrent Chromium
        # crawlers duplicate memory and race to overwrite that shared inventory.
        for active in _RUNS.values():
            if active['process'].poll() is None:
                _RUNS[key] = active
                return active
        _RUNS.clear()
        current = {'process': spawn(), 'category': category, 'mode': mode}
        _RUNS[key] = current
        return current


def get(key):
    with _LOCK:
        return _RUNS.get(key)
