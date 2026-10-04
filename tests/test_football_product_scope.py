from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from src.search_product_policy import product_scope, filter_search_products, football_card_priority
from src.best_alternatives import build_best_alternatives
from src.asking_price_opportunity import select_asking_price_research, attach_asking_price_opportunity
from src.asking_price_ui import positive_price_suggestions
from src.seller_top5 import seller_result_tier, _select_hidden_find_exploration
from src.seller_card_domain import seller_item_domain_check


def listing(index, title, margin=None):
    row = {'titel': title, 'source_category': 'Fotboll', 'pris': 60, 'frakt': 30,
           'lank': f'https://www.tradera.com/item/293310/{index}/card',
           'beslut': 'SKIP', 'analysis_total_cost': 95}
    if margin is not None:
        row['asking_price_opportunity'] = {
            'status': 'POSSIBLE_FIND' if margin > 0 else 'NO_EDGE',
            'possible_find': margin > 0, 'net_margin': margin,
            'reference_asking_price': 150, 'comparison_count': 2,
            'total_cost': 95, 'purchase_price': 60, 'shipping': 30}
    return row


GAME_TITLES = [
    'Lamine Yamal Panini Adrenalyn XL FIFA World Cup 2026 Limited Edition',
    'Topps Match Attax 2024/25 Bukayo Saka Beast Mode BM 2',
    'Panini Adrenalin XL Lionel Messi Gold 01/10 auto',
    'Topps MATCH–ATTAX Lionel Messi 1/1 autograph',
    'Beast Mode Iliman Ndiaye Topps Premier League 2026/27 BM 11',
    'Bukayo Saka Beast Mode Topps 2026/27 BM 2',
]
HOBBY_TITLES = [
    '2023-24 Topps Finest Alexander Isak Prized Footballers #PF-12',
    '2023-24 Panini Prizm Bukayo Saka Blue 12/99 #18',
    '2023-24 Topps Chrome Lamine Yamal autograph #LY',
    '2023-24 Panini Select Lionel Messi patch #LM',
    '2023-24 Topps Merlin Erling Haaland #12',
]


@pytest.mark.parametrize('title', GAME_TITLES + [
    'Hugo Gaston Topps Chrome Tennis kort 17/25',
    '2023-24 Upper Deck NHL Connor Bedard 12/99',
    '2024 Panini Prizm NBA Stephen Curry autograph',
    '2024 Panini NFL Patrick Mahomes 1/1',
])
def test_game_products_and_ordinary_beast_mode_are_hard_excluded(title):
    row = listing(1, title, 1000)
    row.update(decision='KÖP', sold_comps=20, market_value=2000, valuation_display_safe=True)
    assert not product_scope(row)['allowed']
    assert seller_result_tier(row) == 'WEAK'
    assert not seller_item_domain_check(row, 'football')['allowed']
    assert select_asking_price_research([row]) == []
    assert positive_price_suggestions([row]) == []
    assert _select_hidden_find_exploration([dict(row, source_item=row)]) == []
    assert build_best_alternatives([row])['rows'] == []


@pytest.mark.parametrize('title', HOBBY_TITLES + ['Topps Premier League Beast Mode Saka Gold 12/50 BM 2'])
def test_legitimate_hobby_cards_survive(title):
    assert product_scope(listing(1, title))['allowed']


def test_nested_identity_filter_and_no_mutation():
    rows = [{'title': 'Lionel Messi', 'source_item': {'set_name': 'Panini Adrenalyn XL'}},
            {'title': 'Saka', 'exact_identity_gate_identity_fields': {'set_name': 'Match Attax'}},
            listing(3, HOBBY_TITLES[0])]
    original = deepcopy(rows)
    filtered, reasons = filter_search_products(rows)
    assert filtered == [rows[-1]]
    assert reasons == {'EXCLUDED_ADRENALYN': 1, 'EXCLUDED_MATCH_ATTAX': 1}
    assert rows == original


def test_tennis_identity_overrides_wrong_category_but_is_preserved_outside_soccer():
    tennis = {'title': 'Hugo Gaston Topps Chrome Tennis kort 17/25'}
    assert product_scope(tennis)['allowed']
    assert not product_scope(tennis, 'football')['allowed']
    wrongly_categorized = dict(tennis, source_category='Fotboll')
    result = build_best_alternatives([wrongly_categorized, listing(10, HOBBY_TITLES[1])])
    assert len(result['rows']) == 1
    assert result['rows'][0]['title'] == HOBBY_TITLES[1]


def test_old_results_refill_five_with_allowed_losses_and_filter_research_leads():
    rows = [listing(i, title, 1000) for i, title in enumerate(GAME_TITLES)]
    rows += [listing(100+i, title, -i-1) for i, title in enumerate(HOBBY_TITLES)]
    original = deepcopy(rows)
    result = build_best_alternatives(rows, research_leads=[
        {'title': GAME_TITLES[0], 'url': rows[0]['lank'], 'scenario': rows[0]['asking_price_opportunity']}])
    assert len(result['rows']) == result['available_count'] == 5
    assert {r['title'] for r in result['rows']} == set(HOBBY_TITLES)
    assert result['rows'][0]['title'] == HOBBY_TITLES[1]
    assert all(r['decision'] == 'AVSTÅ' and r['market_value'] is None for r in result['rows'])
    assert rows == original


def test_hobby_priority_never_promotes_buy_or_prices_a_card():
    generic = listing(1, 'Alexander Isak Prized Footballers samlarkort')
    numbered = listing(2, HOBBY_TITLES[1])
    assert football_card_priority(generic) == 0
    assert football_card_priority(numbered) == 2
    result = build_best_alternatives([generic, numbered])['rows']
    assert result[0]['title'] == numbered['titel']
    assert all(r['decision'] != 'KÖP' and r['market_value'] is None for r in result)


def test_model_loss_or_tiny_margin_cannot_outrank_numbered_hobby_research():
    numbered = listing(2, 'Topps Simplicidad Rodrigo Riquelme 49/99 Real Betis Balompié')
    numbered['guide_price'] = 37
    weak = listing(1, 'Alexander Isak Prized Footballers samlarkort', 2)
    model = listing(3, 'Erling Haaland Panini Top Class 2023 Rainbow Master Fotbollskort')
    model['guide_price'] = 1000
    result = build_best_alternatives([weak, model, numbered])['rows']
    assert result[0]['title'] == numbered['titel']
    assert all(r['decision'] != 'KÖP' and r['market_value'] is None for r in result)


def test_supported_meaningful_economics_still_precede_hobby_potential():
    numbered = listing(2, HOBBY_TITLES[1])
    positive = listing(1, HOBBY_TITLES[0], 60)
    result = build_best_alternatives([numbered, positive])['rows']
    assert result[0]['title'] == positive['titel']
    assert result[0]['decision'] != 'KÖP'


def test_excluded_attachment_does_not_call_price_api():
    row = listing(1, GAME_TITLES[0])
    with patch('src.asking_price_opportunity.configured_credentials', side_effect=AssertionError('no API route')):
        assert attach_asking_price_opportunity(row) == row


def test_shared_shipping_suggestions_cannot_reintroduce_excluded_products():
    from src.seller_bundle_opportunity import find_same_seller_listings
    current = dict(listing(20, HOBBY_TITLES[0]), saljare='same-seller')
    rows = [dict(listing(i, title), saljare='same-seller') for i, title in enumerate(GAME_TITLES + HOBBY_TITLES)]
    result = find_same_seller_listings(current, rows)
    assert len(result['rows']) == len(HOBBY_TITLES)
    assert all(product_scope(row['source_item'])['allowed'] for row in result['rows'])


def test_ordinary_analysis_rejects_before_fast_or_full_analysis():
    from src.ordinary_analysis_pipeline_v2 import analyze_data
    rows = [listing(i, title) for i, title in enumerate(GAME_TITLES)]
    with patch('src.ebay_browse_context.fetch_configured_quota', return_value={}), \
         patch('src.ordinary_analysis_pipeline_v2.configured_credentials', return_value=(None, None)), \
         patch('src.ebay_browse_context.configured_credentials', return_value=(None, None)), \
         patch('src.ordinary_analysis_pipeline_v2.analyze_item', side_effect=AssertionError('excluded card analysed')):
        results, debug = analyze_data(rows, 'football', '', 500, 'Alla', 5, 'balanced', False, False, False)
    assert results == []
    assert debug['product_scope_rejected'] == len(rows)
    assert debug['cheap_filtered_candidates'] == 0


def test_background_worker_rejects_before_analysis():
    from src.ordinary_analysis_pipeline import analyze_data
    rows = [listing(i, title) for i, title in enumerate(GAME_TITLES)]
    with patch('src.ordinary_analysis_pipeline.analyze_item', side_effect=AssertionError('excluded card analysed')):
        results, debug = analyze_data(rows, 'football', '', 500, 'Alla', 5, 'balanced', False, False, False)
    assert results == []
    assert debug['product_scope_rejected'] == len(rows)


@pytest.mark.parametrize('advanced', [False, True])
def test_app_restores_filtered_five_without_erasing_saved_rows(advanced):
    rows = [listing(i, title, 1000) for i, title in enumerate(GAME_TITLES)]
    rows += [listing(100+i, title, -i-1) for i, title in enumerate(HOBBY_TITLES)]
    original = deepcopy(rows)
    with patch('src.loader.load_data', return_value=[]), patch('importlib.reload', side_effect=lambda module: module):
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=30)
        app.session_state['results'] = rows
        app.session_state['show_advanced_terminal'] = advanced
        app.session_state['debug'] = {'total_items': len(rows), 'price_research_funnel': {'opportunity_attached': len(rows)}}
        app.run()
        assert not app.exception
        table = next(frame.value for frame in app.dataframe if 'Bedömning' in frame.value.columns)
        assert len(table) == 5
        assert not table['Kort'].str.contains('Match Attax|Adrenalyn|Beast Mode', case=False).any()
        assert app.session_state['results'] == original
