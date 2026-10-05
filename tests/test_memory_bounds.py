import tracemalloc
from pathlib import Path
from threading import Event

from src import analysis_cache as cache
from src import background_fetch_registry as fetches
from src import workspace_recovery as recovery
from src.browser_search_backup import encode_snapshot, decode_snapshot
from src.snapshot_encoding import detach_json
from src.resumable_search import new_token


def test_analysis_cache_is_bounded_by_count_and_bytes_and_keeps_latest(monkeypatch, tmp_path):
    monkeypatch.setattr(cache, 'CACHE_PATH', tmp_path / 'analysis.json')
    monkeypatch.setattr(cache, '_memory_cache', None)
    monkeypatch.setattr(cache, 'CACHE_MAX_ENTRIES', 3)
    monkeypatch.setattr(cache, 'CACHE_MAX_BYTES', 1800)
    for n in range(10):
        cache.set_cached_analysis(str(n), {'titel': str(n), 'description': 'x' * 700})
    entries = cache._load_cache_payload()['entries']
    assert len(entries) <= 3
    assert sum(row['size_bytes'] for row in entries.values()) <= 1800
    assert cache.get_cached_analysis('9')['titel'] == '9'
    assert cache.get_cached_analysis('0') is None
    monkeypatch.setattr(cache, '_memory_cache', None)
    assert cache.get_cached_analysis('9')['titel'] == '9'


def test_oversized_old_analysis_cache_is_not_deserialized(monkeypatch, tmp_path):
    path = tmp_path / 'analysis.json'
    with path.open('wb') as handle:
        handle.truncate(cache.CACHE_MAX_BYTES * 2 + 1)
    monkeypatch.setattr(cache, 'CACHE_PATH', path)
    monkeypatch.setattr(cache, '_memory_cache', None)
    monkeypatch.setattr(cache.json, 'load', lambda *a: (_ for _ in ()).throw(AssertionError('Oversized cache read')))
    assert cache.get_cached_analysis('old') is None
    assert path.exists()


def test_workspace_copy_avoids_whole_description_text_duplication():
    rows = [{'titel': f'Card {n}', 'full_description': 'x' * 4000,
             'detail': {'price': n, 'reasons': ['model']}} for n in range(2000)]
    tracemalloc.start()
    try:
        saved = recovery.snapshot({'results': rows}, {})
        validated = recovery.validate(saved)
        _, peak = tracemalloc.get_traced_memory()
        assert peak < 6 * 1024 * 1024
    finally:
        tracemalloc.stop()
    assert len(validated['state']['results']) == 2000
    rows[0]['detail']['price'] = -1
    assert saved['state']['results'][0]['detail']['price'] == 0
    assert validated['state']['results'][0]['detail']['price'] == 0


def test_streamed_browser_backup_keeps_results_and_dismissals():
    token = new_token()
    rows = [{'titel': f'Card {n}', 'full_description': 'å' * 4000} for n in range(1000)]
    saved = {'status': 'COMPLETED', 'params': {'widgets': {}}, 'results': rows,
             'debug': {'workspace': {'dismissed_keys': ['5']}}}
    blob = encode_snapshot(token, saved)
    assert blob
    assert decode_snapshot(token, blob) == saved


def test_unknown_objects_and_shared_containers_are_safe_detached():
    shared = {'text': 'description', 'value': 10}
    original = {'results': [shared, shared], 'process': object(), 'tuple': (1, 2)}
    saved = detach_json(original)
    assert saved['process'] is None and saved['tuple'] == [1, 2]
    assert saved['results'][0] is saved['results'][1]
    shared['value'] = 20
    assert saved['results'][0]['value'] == 10


def test_two_workspaces_share_one_crawler_and_can_start_after_completion(monkeypatch):
    monkeypatch.setattr(fetches, '_RUNS', {})
    class Process:
        code = None
        def poll(self): return self.code
    calls = []
    def spawn():
        process = Process()
        calls.append(process)
        return process
    first = fetches.start('mobile', spawn, category='football', mode='market')
    second = fetches.start('desktop', spawn, category='hockey', mode='latest')
    assert first is second and len(calls) == 1
    assert fetches.get('desktop')['category'] == 'football'
    first['process'].code = 0
    third = fetches.start('desktop', spawn, category='hockey', mode='latest')
    assert third is not first and len(calls) == 2
    assert third['category'] == 'hockey'


def test_pending_remote_work_keeps_file_paths_instead_of_result_copies(monkeypatch, tmp_path):
    monkeypatch.setattr(recovery, '_ROOT', tmp_path)
    monkeypatch.setattr(recovery, '_PENDING', {})
    monkeypatch.setattr(recovery, '_BACKUP_ACTIVE', set())
    entered, release = Event(), Event()
    calls = []
    def slow_save(db, namespace, payload):
        calls.append(payload)
        entered.set()
        release.wait(3)
    monkeypatch.setattr(recovery, 'save_namespace', slow_save)
    token = new_token()
    try:
        recovery.save(token, recovery.snapshot({'results': [{'titel': 'first'}]}, {}), 'db')
        assert entered.wait(1)
        recovery.save(token, recovery.snapshot({'results': [{'titel': 'latest'}]}, {}), 'db')
        assert isinstance(recovery._PENDING[token][1], Path)
        assert recovery.load(token)['state']['results'][0]['titel'] == 'latest'
    finally:
        release.set()


def test_unchanged_workspace_does_not_recompress_browser_backup(monkeypatch, tmp_path):
    import src.inline_components as components
    import src.browser_search_backup as backup
    monkeypatch.setattr(recovery, '_ROOT', tmp_path)
    token = new_token()
    monkeypatch.setattr(components, 'mount_inline', lambda *a, **k: {'token': token})
    state, query = {'results': [{'titel': 'Messi'}]}, {'view_run': token}
    recovery.recover_ui(state, query)
    recovery.recover_ui(state, query)
    monkeypatch.setattr(backup, 'encode_snapshot', lambda *a: (_ for _ in ()).throw(AssertionError('Unchanged snapshot recompressed')))
    recovery.recover_ui(state, query)
    assert state['results'][0]['titel'] == 'Messi'
