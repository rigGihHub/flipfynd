from pathlib import Path
from unittest.mock import patch
import time
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest
from src import resumable_search as jobs


@pytest.fixture(autouse=True)
def isolate_market_cache():
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def test_normal_search_submits_and_recovers_completed_results_without_error():
    listings = [{'tradera_item_id': 'test-normal-1', 'titel': '2024 Upper Deck Connor McDavid',
                 'pris': 20, 'frakt': 20, 'sport': 'hockey', 'category': 'Hockey - NHL', 'source_category': 'Hockey - NHL',
                 'url': 'https://www.tradera.com/item/293316/1/test'}]
    def load(path):
        return listings if str(path).endswith('tradera_data.json') else []
    with patch('src.loader.load_data', side_effect=load), \
            patch('src.ordinary_analysis_pipeline_v2.analyze_data', return_value=([], {'mode': 'test'})) as analyze, \
            patch('importlib.reload', side_effect=lambda module: module):
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=30).run()
        find = next(button for button in app.button if button.label == '🔎 Hitta fynd')
        assert not find.disabled
        find.click().run()
        assert not app.exception
        token = app.query_params['search_run']
        if isinstance(token, list):
            token = token[0]
        for _ in range(200):
            job = jobs.load(token)
            if job and job['status'] != 'RUNNING':
                break
            time.sleep(.01)
        assert jobs.load(token)['status'] == 'COMPLETED'
        app.run()
        assert not app.exception
        analyze.assert_called_once()
        assert analyze.call_args.kwargs['data'] == listings
        assert app.session_state['results'] == []
        assert app.session_state['debug'] == {'mode': 'test'}


def test_continue_passes_checkpoint_but_changed_filters_start_fresh():
    listings = [{'tradera_item_id': 'test-resume-1', 'titel': '2023-24 Upper Deck #451 Connor Bedard',
                 'pris': 20, 'frakt': 20, 'source_category': 'Hockey - NHL'}]
    checkpoint = {'updated_at': time.time(), 'completed': ['a' * 64]}
    def load(path):
        return listings if str(path).endswith('tradera_data.json') else []
    with patch('src.loader.load_data', side_effect=load), \
            patch('src.ordinary_analysis_pipeline_v2.analyze_data', return_value=([], {
                'inventory_price_remaining': 1, 'research_checkpoint': checkpoint})) as analyze, \
            patch('importlib.reload', side_effect=lambda module: module):
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=30).run()
        def submit(label):
            next(button for button in app.button if button.label == label).click().run()
            token = app.query_params['search_run']
            if isinstance(token, list):
                token = token[0]
            for _ in range(200):
                if jobs.load(token)['status'] != 'RUNNING':
                    break
                time.sleep(.01)
            assert jobs.load(token)['status'] == 'COMPLETED'
            app.run()
            assert not app.exception
        submit('🔎 Hitta fynd')
        assert 'research_checkpoint' not in analyze.call_args.kwargs
        submit('🔎 Fortsätt hitta fynd')
        assert analyze.call_args.kwargs['research_checkpoint'] == checkpoint
        app.number_input(key='search_budget').set_value(2000).run()
        submit('🔎 Sök med nuvarande filter')
        assert 'research_checkpoint' not in analyze.call_args.kwargs
