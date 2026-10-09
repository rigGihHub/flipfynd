from copy import deepcopy
from pathlib import Path
import time
from unittest.mock import patch

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest
from src import resumable_search, workspace_recovery, background_fetch_registry
from src.search_experience import clear_results, pending_phase, pending_search, result_context
from src.best_alternatives import build_best_alternatives, candidate_presentation

APP = Path(__file__).resolve().parents[1] / 'app.py'


def listing(n=1, **extra):
    return {'titel': f'Lionel Messi On-Card Auto /25 {n}', 'pris': 40,
            'source_category': 'Fotboll', 'lank': f'https://www.tradera.com/item/293311/{n}/card', **extra}


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    st.cache_data.clear()
    monkeypatch.setattr(resumable_search, '_ROOT', tmp_path / 'jobs')
    monkeypatch.setattr(workspace_recovery, '_ROOT', tmp_path / 'views')
    monkeypatch.setattr(background_fetch_registry, '_RUNS', {})
    yield
    st.cache_data.clear()


def test_clear_results_preserves_market_fetch_and_seller_state():
    state = {'results': [listing()], 'debug': {}, 'result_cache': {'a': 1},
             'seller_top5_result': {'rows': [listing(3)]}, 'fetch_status': 'running',
             'pending_find_request': {'category': 'Fotboll'}, 'search_budget': 500}
    query = {'search_run': 'a' * 32, 'seller_run': 'b' * 32, 'view_run': 'c' * 32}
    clear_results(state, query)
    assert state['results'] is None and state['debug'] is None
    assert state['seller_top5_result']['rows'] and state['fetch_status'] == 'running'
    assert state['search_budget'] == 500 and 'pending_find_request' not in state
    assert query == {'seller_run': 'b' * 32, 'view_run': 'c' * 32}


def test_result_context_keeps_saved_filters_and_explains_changes():
    snapshot = {'params': {'widgets': {'search_sport': 'Fotboll', 'search_budget': 500,
                                     'search_text': 'Messi'}}, 'completed_at': 1791540000}
    original = deepcopy(snapshot)
    view = result_context(snapshot, {'search_sport': 'Hockey', 'search_budget': 800})
    assert 'Fotboll' in view['label'] and '500 kr' in view['label'] and 'Messi' in view['label']
    assert '2026-' in view['label'] and view['changed']
    assert snapshot == original
    assert 'Filter ej sparade' in result_context(None, {})['label']


def test_pending_waits_for_its_own_sport_and_roundtrips_workspace():
    state = {'search_sport': 'Fotboll', 'search_budget': 500, 'search_text': 'Messi'}
    request = pending_search(state, 'Fotboll')
    state['search_sport'] = 'Hockey'
    assert request['widgets']['search_sport'] == 'Fotboll'
    assert pending_phase(request, 'running', 'Hockey - NHL') == 'WAIT'
    assert pending_phase(request, 'finished', 'Hockey - NHL') == 'FAILED'
    assert pending_phase(request, 'finished', 'Fotboll') == 'READY'
    saved = workspace_recovery.snapshot({'pending_find_request': request}, {})
    restored = {}
    workspace_recovery.restore(restored, {}, saved)
    assert restored['pending_find_request'] == request


def test_candidate_unknown_prices_keep_real_images_and_no_zero_rating():
    raw = listing(image_urls=['https://img.example.com/front.jpg', 'https://img.example.com/back.jpg',
                              'file:///private', 'javascript:alert(1)'], expected_resale=1000000)
    row = build_best_alternatives([raw])['rows'][0]
    view = candidate_presentation(row)
    assert view['status'] == 'Granska' and view['price'] == 'Okänt'
    assert view['potential'] == view['certainty'] == 'Ej bedömd'
    assert view['images'] == raw['image_urls'][:2]
    assert any(label == 'Antagen frakt' for label, value in view['costs']['parts'])
    assert not view['summary']['available']


def test_known_negative_margin_is_not_presented_as_a_buy():
    view = candidate_presentation({'title': 'Messi', 'decision': 'KÖP', 'practical_margin': -10})
    assert view['status'] == 'Avstå'


class FetchProcess:
    code = None
    def poll(self):
        return self.code
    def terminate(self):
        self.code = -15


def await_job(app):
    token = app.query_params['search_run']
    if isinstance(token, list):
        token = token[0]
    for _ in range(200):
        if resumable_search.load(token)['status'] != 'RUNNING':
            break
        time.sleep(.01)
    assert resumable_search.load(token)['status'] == 'COMPLETED'
    return token


def test_one_click_fetches_then_analyzes_original_filters_even_after_reopening():
    rows = []
    process = FetchProcess()
    def load(path):
        return rows if str(path).endswith('tradera_data.json') else []
    with patch('src.loader.load_data', side_effect=load), \
         patch('subprocess.Popen', return_value=process) as spawn, \
         patch('src.ordinary_analysis_pipeline_v2.analyze_data', return_value=([], {'tested': True})) as analyze, \
         patch('importlib.reload', side_effect=lambda module: module):
        app = AppTest.from_file(APP, default_timeout=30)
        app.query_params['view_run'] = 'd' * 32
        app.run()
        app.selectbox(key='search_sport').set_value('Fotboll')
        app.number_input(key='search_budget').set_value(450)
        app.text_input(key='search_text').set_value('Messi')
        next(b for b in app.button if b.label == '🔎 Hitta fynd').click().run()
        assert not app.exception
        assert 'search_run' not in app.query_params and spawn.call_count == 1
        assert app.session_state['pending_find_request']['widgets']['search_budget'] == 450
        assert next(b for b in app.button if b.label == '⏳ Vänta – annonser hämtas').disabled
        app.run()
        assert spawn.call_count == 1 and not analyze.called
        view_token = app.query_params['view_run']
        rows.append(listing())
        process.code = 0
        fresh = AppTest.from_file(APP, default_timeout=30)
        fresh.query_params['view_run'] = view_token
        fresh.run()
        assert not fresh.exception, [e.message for e in fresh.exception]
        await_job(fresh)
        fresh.run()
        assert not fresh.exception and analyze.call_count == 1
        assert analyze.call_args.kwargs['sport'] == 'football'
        assert analyze.call_args.kwargs['max_price'] == 450
        assert analyze.call_args.kwargs['search'] == 'Messi'
        assert 'pending_find_request' not in fresh.session_state
        assert spawn.call_count == 1


def test_tom_resultat_in_real_app_never_deletes_loaded_market():
    rows = [listing()]
    with patch('src.loader.load_data', side_effect=lambda p: rows if str(p).endswith('tradera_data.json') else []), \
         patch('importlib.reload', side_effect=lambda m: m), \
         patch('src.tradera_fetcher.clear_all_loaded_data') as delete_market:
        app = AppTest.from_file(APP, default_timeout=30)
        app.session_state['results'] = rows
        app.session_state['debug'] = {}
        app.run()
        next(b for b in app.button if b.label == 'Töm resultat').click().run()
        assert not app.exception
        assert app.session_state['results'] is None
        delete_market.assert_not_called()
        assert not next(b for b in app.button if b.label == '🔎 Hitta fynd').disabled


def test_real_candidate_ui_has_direct_actions_and_optional_comparison():
    rows = [listing(n) for n in range(1, 6)]
    with patch('src.loader.load_data', return_value=[]), patch('importlib.reload', side_effect=lambda m: m):
        app = AppTest.from_file(APP, default_timeout=30)
        app.session_state['results'] = rows
        app.session_state['debug'] = {}
        app.run()
        assert not app.exception
        assert len([x for x in app.get('link_button') if x.label == 'Öppna annonsen ↗']) == 5
        text = '\n'.join(str(x.value) for x in list(app.markdown) + list(app.caption))
        assert 'Annonsbild saknas' in text and 'Kontrollera först' in text
        assert 'modell/guide' not in text
        assert any(e.label == 'Jämför alternativen i tabell' and not e.proto.expanded for e in app.expander)
        assert not any(e.label.startswith('#1 ·') for e in app.expander)


def test_refresh_uses_visible_sport_without_analysis_submit():
    rows = [dict(listing(), source_category='Hockey - NHL')]
    process = FetchProcess()
    with patch('src.loader.load_data', side_effect=lambda p: rows if str(p).endswith('tradera_data.json') else []), \
         patch('subprocess.Popen', return_value=process) as spawn, \
         patch('importlib.reload', side_effect=lambda m: m):
        app = AppTest.from_file(APP, default_timeout=30).run()
        app.selectbox(key='search_sport').set_value('Fotboll').run()
        assert not app.exception
        app.button(key='top_fetch_selected').click().run()
        assert not app.exception
        command = spawn.call_args.args[0]
        assert command[command.index('--category') + 1] == 'Fotboll'
        assert 'search_run' not in app.query_params


def test_tom_resultat_is_locked_while_analysis_is_running():
    token = 'e' * 32
    job = {'status': 'RUNNING', 'token': token, 'started_at': time.time(),
           'params': {'widgets': {'search_sport': 'Fotboll', 'search_budget': 500}},
           'results': [], 'debug': {}}
    with patch('src.loader.load_data', return_value=[]), \
         patch('src.resumable_search.load', side_effect=lambda t, *a: job if t == token else None), \
         patch('importlib.reload', side_effect=lambda m: m):
        app = AppTest.from_file(APP, default_timeout=30)
        app.query_params['search_run'] = token
        app.run()
        assert not app.exception
        assert app.button(key='clear_main_results').disabled
        assert app.button(key='run_main_search').disabled
        assert app.button(key='reset_main_market').disabled


def test_failed_fetch_does_not_create_an_analysis_or_discard_old_results():
    old = [listing()]
    with patch('src.loader.load_data', return_value=[]), \
         patch('src.ordinary_analysis_pipeline_v2.analyze_data') as analyze, \
         patch('importlib.reload', side_effect=lambda m: m):
        app = AppTest.from_file(APP, default_timeout=30)
        app.session_state['results'] = old
        app.session_state['pending_find_request'] = pending_search({'search_sport': 'Fotboll'}, 'Fotboll')
        app.session_state['fetch_status'] = 'failed'
        app.run()
        assert not app.exception
        assert app.session_state['results'] == old
        assert 'pending_find_request' not in app.session_state
        analyze.assert_not_called()
        assert any('Tryck Hitta fynd' in x.value for x in app.error)
