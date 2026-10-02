from threading import Event, Thread
import time
from src import search_progress as progress
from src import resumable_search as jobs
from src import seller_round_job
from src import seller_top5_controller as controller
from tests.test_seller_search_continuation import item, analyze


def test_eta_uses_current_phase_and_is_reset_between_steps(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(progress.time, 'monotonic', lambda: now[0])
    events = []
    with progress.track_progress(events.append):
        progress.begin_phase('Djupanalyserar kort', 4, unit='kort')
        now[0] += 8
        progress.report_phase('Djupanalyserar kort', checked=1, total=4, unit='kort', fraction=.73)
        assert events[-1]['eta_seconds'] == 24
        label, text, fraction = progress.progress_text({'started_at': time.time()-15, 'progress': events[-1]})
        assert 'cirka 24 s kvar i detta steg' in text and 'tid hittills: 15 s' in text
        assert fraction == .73 and label == 'Djupanalyserar kort'
        progress.begin_phase('Uppdaterar topp 5', 0)
        assert 'eta_seconds' not in events[-1]
        assert events[-1]['checked'] == 0 and events[-1]['total'] == 0


def test_status_reads_do_not_wait_for_slow_database_write(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, '_ROOT', tmp_path)
    monkeypatch.setattr(jobs, 'load_namespace', lambda *args: None)
    storing, release, read_done = Event(), Event(), Event()
    def slow_save(*args):
        storing.set()
        release.wait(2)
    monkeypatch.setattr(jobs, 'save_namespace', slow_save)
    token = jobs.new_token()
    assert jobs.start(token, {}, lambda: ([{'id':'1'}], {}), database_url='postgresql://test')
    try:
        assert storing.wait(1)
        readings = []
        def read():
            readings.append(jobs.load(token))
            read_done.set()
        thread = Thread(target=read)
        thread.start()
        assert read_done.wait(.3), 'Status panel blocked behind database storage'
        assert readings[0]['status'] == 'COMPLETED'
    finally:
        release.set()
        thread.join(2)


def test_seller_worker_reports_real_phase_time_and_shorter_round(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, '_ROOT', tmp_path)
    token = jobs.new_token()
    checked = Event()
    def resolve(seller, items, **kwargs):
        assert kwargs['full_limit'] == 4 and kwargs['public_pages'] == 2
        cb = kwargs['progress_callback']
        cb({'phase':'full_start','done':0,'total':4,'percent':66})
        cb({'phase':'full_progress','done':1,'total':4,'percent':73})
        report = jobs.load(token)['progress']
        assert report['phase'] == 'Djupanalyserar kort'
        assert report['checked'] == 1 and report['total'] == 4
        assert report['fraction'] == .73 and 'eta_seconds' in report
        checked.set()
        return {'rows':[], 'inventory_source':'PROFILE'}
    assert seller_round_job.start(token, seller='seller', profile_url='', market_items=[],
                                  analyze_fn=analyze, resolve_fn=resolve)
    assert checked.wait(2)


def test_four_card_round_keeps_registry_and_rotates_to_unseen_cards():
    inventory = [item(i) for i in range(100)]
    calls = []
    def track(source, **kwargs):
        if kwargs.get('mode') == 'full': calls.append(source['tradera_item_id'])
        return analyze(source, **kwargs)
    args = dict(analyze_fn=track, quick_limit=60, full_limit=4, source='TEST', progress_callback=lambda _: None)
    first = controller._rank('seller', inventory, **args)
    assert 0 < len(calls) <= 4 and first['round_full_limit'] == 4
    initial = set(calls)
    calls.clear()
    second = controller._rank('seller', inventory, analysis_registry=first['analysis_registry'], **args)
    assert 0 < len(calls) <= 4 and not initial & set(calls)
    assert second['full_unique_analysed'] > first['full_unique_analysed']
