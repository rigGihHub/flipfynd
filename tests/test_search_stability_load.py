import json
from pathlib import Path
import subprocess
import sys
import tracemalloc

from src import resumable_search as jobs


def test_completed_search_snapshot_streams_without_allocating_full_encoded_copies(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, '_ROOT', tmp_path)
    payload = {'status': 'COMPLETED', 'results': [
        {'titel': str(n), 'full_description': 'å' * 4000} for n in range(2000)]}
    token = jobs.new_token()
    tracemalloc.start()
    try:
        jobs._save(token, payload)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 2 * 1024 * 1024
    assert len(jobs.load(token)['results']) == 2000


def test_repeated_rounds_disconnects_restarts_and_removals_under_load():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(root / 'scripts/check_search_stability.py'),
                             '--rounds', '8', '--rows', '200'], cwd=root,
                            capture_output=True, text=True, timeout=90, check=True)
    report = json.loads(result.stdout)
    assert report['status'] == 'passed' and report['rounds'] == 8
    assert report['duplicate_jobs'] == 0 and report['restored_removed_cards'] == 0
