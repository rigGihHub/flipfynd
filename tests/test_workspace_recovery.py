from threading import Event
import time
import pytest
from src import workspace_recovery as recovery
from src import resumable_search as jobs
from src import seller_round_job
from src import background_fetch_registry as fetches


def test_restore_entire_workspace_and_dismissals_after_new_session(monkeypatch, tmp_path):
    monkeypatch.setattr(recovery, '_ROOT', tmp_path)
    token = jobs.new_token()
    original = {'search_text': 'Bedard', 'search_budget': 750,
                'show_advanced_terminal': True, 'results': [{'titel': 'A'}],
                'seller_top5_result': {'rows': [{'id': '6'}], 'analysis_registry': {'hidden_row_keys': ['5']}},
                'fetch_status': 'running', 'seller_inventory_result_cardland': {'next_page': 7},
                'fetch_process': object(), 'password': 'secret', 'seller_top5_pending_request': True}
    query = {'view_run': token, 'seller_run': jobs.new_token()}
    assert recovery.persist_current(original, query)
    recovery._HASHES.clear()  # New Python process can read durable snapshots.
    restored, restored_query = {}, {'view_run': token}
    recovery.restore(restored, restored_query, recovery.load(token))
    assert restored['results'] == original['results']
    assert restored['seller_top5_result'] == original['seller_top5_result']
    assert restored['seller_inventory_result_cardland']['next_page'] == 7
    assert restored['search_budget'] == 750
    assert restored_query['seller_run'] == query['seller_run']
    assert not {'password', 'fetch_process', 'seller_top5_pending_request'} & restored.keys()
    assert recovery.load(jobs.new_token()) is None
    assert recovery.load('../bad') is None


def test_explicit_clear_is_persisted_not_resurrected(monkeypatch, tmp_path):
    monkeypatch.setattr(recovery, '_ROOT', tmp_path)
    token = jobs.new_token()
    recovery.save(token, recovery.snapshot({'seller_top5_result': {'rows': [1]}}, {'seller_run': jobs.new_token()}))
    recovery.save(token, recovery.snapshot({'results': None}, {}))
    state, query = {}, {}
    recovery.restore(state, query, recovery.load(token))
    assert 'seller_top5_result' not in state and 'seller_run' not in query
    assert state['results'] is None


def test_browser_drafts_are_newer_bounded_and_type_checked():
    value = recovery.snapshot({'search_budget': 500, 'search_text': 'old'}, {}) | {'updated_at': 10}
    state = {'search_budget': 1000, 'search_text': ''}  # Defaults already rendered before browser reply.
    recovery.restore(state, {}, value, {'at': 11, 'widgets': {'search_text': 'new', 'search_budget': 800}}, replace=True)
    assert state == {'search_budget': 800, 'search_text': 'new'}
    for bad in [None, {'at': 'bad'}, {'at': 20, 'widgets': []}, {'at': 20, 'widgets': {'search_budget': float('nan'), 'search_sport': 'invalid', 'fetch_process': 'bad'}}]:
        recovery.restore(state, {}, value, bad)
    assert state['search_budget'] == 800 and 'search_sport' not in state
    recovery.restore(state, {}, value, {'at': 9, 'widgets': {'search_text': 'older'}})
    assert state['search_text'] == 'new'


def test_seller_round_survives_session_loss_without_duplicate_work(monkeypatch, tmp_path):
    monkeypatch.setattr(jobs, '_ROOT', tmp_path)
    token = jobs.new_token()
    entered, release = Event(), Event()
    calls = []
    def resolve(seller, items, **kwargs):
        calls.append((seller, items, kwargs['resume_checkpoint'], kwargs['analysis_registry']))
        entered.set()
        assert release.wait(3)
        return {'rows': [{'id': '6'}], 'public_checkpoint': {'next_page': 7}, 'inventory_source': 'PROFILE'}
    kwargs = dict(seller='Cardland', profile_url='https://www.tradera.com/profile/items/6160765/',
                  market_items=[], analyze_fn=lambda x: x, checkpoint={'next_page': 4},
                  registry={'hidden_row_keys': ['5']}, resolve_fn=resolve)
    assert seller_round_job.start(token, **kwargs)
    assert entered.wait(1)
    assert jobs.load(token)['status'] == 'RUNNING'
    assert not seller_round_job.start(token, **kwargs)
    release.set()
    for _ in range(100):
        if jobs.load(token)['status'] != 'RUNNING':
            break
        time.sleep(.01)
    result = jobs.load(token)
    assert result['status'] == 'COMPLETED'
    assert result['results'][0]['public_checkpoint']['next_page'] == 7
    assert len(calls) == 1 and calls[0][3] == {'hidden_row_keys': ['5']}
    jobs._JOBS.pop(token)
    assert jobs.load(token)['results'] == result['results']


def test_fetch_process_is_shared_between_sessions_and_replaced_after_completion():
    class Process:
        code = None
        def poll(self): return self.code
    calls = []
    def spawn():
        process = Process()
        calls.append(process)
        return process
    key = jobs.new_token()
    first = fetches.start(key, spawn, category='hockey', mode='latest')
    assert fetches.start(key, spawn, category='football', mode='market') is first
    assert fetches.get(key) is first and len(calls) == 1
    first['process'].code = 0
    assert fetches.start(key, spawn, category='football', mode='market') is not first
    assert len(calls) == 2


def test_new_streamlit_session_restores_filters_results_and_clear(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest
    from pathlib import Path
    monkeypatch.setattr(recovery, '_ROOT', tmp_path)
    token = jobs.new_token()
    recovery.save(token, recovery.snapshot({'search_sport': 'Fotboll', 'search_budget': 600,
        'search_text': 'Messi', 'show_advanced_terminal': True,
        'seller_top5_alias': 'Cardland', 'seller_top5_profile_url': 'https://www.tradera.com/profile/items/6160765/',
        'seller_top5_result': {'status': 'OK', 'seller': 'Cardland', 'inventory_count': 6, 'rows': []}}, {}))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30)
    app.query_params['view_run'] = token
    app.run()
    assert not app.exception
    assert app.selectbox(key='search_sport').value == 'Fotboll'
    assert app.number_input(key='search_budget').value == 600
    assert app.text_input(key='search_text').value == 'Messi'
    assert app.session_state['seller_top5_result']['inventory_count'] == 6
    app.button(key='seller_top5_clear').click().run()
    assert not app.exception
    assert ('seller_top5_result' not in app.session_state or not app.session_state['seller_top5_result'])
    fresh = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30)
    fresh.query_params['view_run'] = token
    fresh.run()
    assert not fresh.exception
    assert ('seller_top5_result' not in fresh.session_state or not fresh.session_state['seller_top5_result'])


def test_disk_failure_does_not_crash_ui_or_job(monkeypatch, tmp_path):
    bad_root = tmp_path / 'file'
    bad_root.write_text('not a directory')
    monkeypatch.setattr(recovery, '_ROOT', bad_root)
    monkeypatch.setattr(jobs, '_ROOT', bad_root)
    token = jobs.new_token()
    assert not recovery.save(token, recovery.snapshot({'search_text': 'saved'}, {}))
    assert jobs.start(token, {}, lambda: ([{'id': '1'}], {}))
    for _ in range(100):
        if jobs.load(token)['status'] != 'RUNNING': break
        time.sleep(.01)
    assert jobs.load(token)['status'] == 'COMPLETED'


def test_unsent_advanced_filters_restore_with_enum_and_range_checks():
    state = {}
    recovery.restore(state, {}, recovery.snapshot({}, {}), {'at': time.time(), 'widgets': {
        'search_sport': 'Fotboll', 'search_archive': True, 'search_show_count': 8,
        'search_sale_type': 'Endast Köp nu', 'search_minimum_confidence': .5,
        'ordinary_card_type_filter': 'Endast autograf', 'search_show_skip': False}})
    assert state['search_sport'] == 'Fotboll' and state['search_show_count'] == 8
    assert state['ordinary_card_type_filter'] == 'Endast autograf'
