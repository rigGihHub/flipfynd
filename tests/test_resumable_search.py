from threading import Event
import time
from src import resumable_search as jobs


def test_disconnect_recovers_running_then_completed_without_duplicate(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, '_ROOT', tmp_path)
    entered, release = Event(), Event()
    token = jobs.new_token()
    calls = []
    def work():
        calls.append(1)
        entered.set()
        release.wait(2)
        return [{'titel': 'Result'}], {'final_results': 1}
    assert jobs.start(token, {'widgets': {'search_budget': 500}}, work)
    assert entered.wait(1)
    assert jobs.load(token)['status'] == 'RUNNING'
    assert not jobs.start(token, {}, work)
    release.set()
    for _ in range(100):
        if jobs.load(token)['status'] == 'COMPLETED':
            break
        time.sleep(.01)
    assert calls == [1]
    with jobs._LOCK:
        jobs._JOBS.pop(token)
    saved = jobs.load(token)
    assert saved['status'] == 'COMPLETED'
    assert saved['results'][0]['titel'] == 'Result'
    assert saved['params']['widgets']['search_budget'] == 500
    assert jobs.load(jobs.new_token()) is None
    assert jobs.load('../invalid') is None


def test_process_interruption_is_not_an_eternally_running_job(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, '_ROOT', tmp_path)
    token = jobs.new_token()
    jobs._save(token, {'status': 'RUNNING', 'params': {'sport': 'hockey'}})
    assert jobs.load(token)['status'] == 'INTERRUPTED'


def test_evicted_completed_jobs_remain_recoverable(monkeypatch, tmp_path):
    from src import resumable_search as jobs
    import time
    monkeypatch.setattr(jobs, '_ROOT', tmp_path)
    monkeypatch.setattr(jobs, '_JOBS', {})
    tokens = []
    for index in range(4):
        token = jobs.new_token()
        tokens.append(token)
        assert jobs.start(token, {}, lambda i=index: ([{'id': str(i)}], {}), fresh=True)
        for _ in range(100):
            if jobs.load(token)['status'] == 'COMPLETED':
                break
            time.sleep(.01)
        assert jobs.load(token)['status'] == 'COMPLETED'
    assert len(jobs._JOBS) == 2
    assert tokens[0] not in jobs._JOBS
    assert jobs.load(tokens[0])['results'] == [{'id': '0'}]
