from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from src.best_alternatives import build_best_alternatives
from src.card_parser import parse_card_features
from src.candidate_review import build_candidate_review
from src.adaptive_deepening import select_adaptive_full_analysis_indices, merge_deep_analysis_routes
from src.candidate_coverage import diversify_full_analysis_indices
from src.fast_analysis_pool import select_fast_analysis_pool
from src.seller_collector_signals import collector_signals
from src.ebay_browse_context import match_active_rows
from src.premium_comp_hunter import hunt_premium_comps
from src.analyzer import get_listing_features
from src.exact_identity_gate import build_exact_identity_gate

MESSI = 'Lionel Messi Superior Signatures Legends On-Card Auto /25 – 12/25'


def listing(n, title=None, **extra):
    return {'titel': title or f'2023-24 Topps Chrome Lionel Messi #{n}',
            'source_category': 'Fotboll', 'pris': 16, 'frakt': 29,
            'analysis_total_cost': 45, 'lank': f'https://www.tradera.com/item/293311/{n}/card',
            'tradera_item_id': str(n), **extra}


def test_messi_identity_keeps_copy_separate_and_does_not_invent_product_year_or_number():
    item = listing(1, MESSI, expected_resale=57)
    original = deepcopy(item)
    features = parse_card_features(MESSI)
    assert features['serial_number'] == 25 and features['serial_copy_number'] == 12
    assert features['autograph_type'] == 'on_card'
    assert features['card_number'] is None and features['year'] is None
    review = build_candidate_review(item)
    assert {'set/program', 'säsong/år', 'kortnummer'} <= set(review['identity']['missing'])
    assert any('12/25' in reason for reason in review['reasons'])
    assert any('äkthet' in check for check in review['checks'])
    assert item == original


@pytest.mark.parametrize('title', [
    'Lionel Messi printed signature auto /25', 'Lionel Messi tryckt autograf /25',
    'Lionel Messi ej signerad /25', 'Lionel Messi facsimile on-card auto /25',
])
def test_printed_or_denied_autograph_never_earns_autograph_priority(title):
    assert not parse_card_features(title)['is_auto']
    assert 'autograph' not in collector_signals({'titel': title})['signals']
    assert not any('anger autograf' in text for text in build_candidate_review({'titel': title})['reasons'])


def test_swedish_autograph_and_unusual_serial_runs_are_not_missed():
    for title in ['Messi autograf 8/8', 'Ronaldinho signerad 16/19', 'Topps Chrome RC 14/350']:
        assert 'serial_numbered' in collector_signals({'titel': title})['signals']
    assert 'autograph' in collector_signals({'titel': 'Messi autograf 8/8'})['signals']
    assert 'serial_numbered' not in collector_signals({'titel': '2024/25 Topps Chrome'})['signals']


@pytest.mark.parametrize('kind', ['Sticker Auto', 'Auto'])
def test_on_card_target_cannot_inherit_sticker_or_unknown_autograph_prices(kind):
    title = f'Lionel Messi 2023-24 Topps Chrome #{17} {kind} /25'
    identity = {'player_name': 'Lionel Messi', 'season': '2023-24', 'set_name': 'Topps Chrome',
                'card_number': '17', 'is_auto': True, 'autograph_type': 'on_card', 'serial_denominator': 25}
    active = match_active_rows([{'title': title, 'buying_options': ['FIXED_PRICE'], 'price': 500}], identity)
    assert not any(row['asking_comparison_eligible'] for row in active)
    sold = {'title': title, 'market_state': 'sold', 'sold_price': 500,
            'sold_verification_status': 'verified', 'sale_evidence_type': 'explicit_sold_price', 'platform': 'manual'}
    premium = hunt_premium_comps(dict(identity, serial_number=25), [sold, dict(sold, sold_price=600)])
    assert premium['exact_count'] == 0 and not premium['safe_for_valuation']


def test_exact_on_card_comparisons_still_remain_usable():
    title = 'Lionel Messi 2023-24 Topps Chrome #17 On-Card Auto /25'
    identity = {'player_name': 'Lionel Messi', 'season': '2023-24', 'set_name': 'Topps Chrome',
                'card_number': '17', 'is_auto': True, 'autograph_type': 'on_card', 'serial_denominator': 25}
    active = match_active_rows([{'title': title, 'buying_options': ['FIXED_PRICE'], 'price': 500}], identity)
    assert len(active) == 1 and active[0]['asking_comparison_eligible']


def test_conflicting_autograph_type_in_description_locks_exact_identity():
    features = get_listing_features({'titel': 'Lionel Messi 2023-24 Topps Chrome #17 On-Card Auto /25',
                                     'full_description': 'Lionel Messi 2023-24 Topps Chrome #17 Sticker Auto /25'}, 'football')
    assert any('autograph_type' in conflict for conflict in features['identity_conflicts'])
    assert not build_exact_identity_gate(features)['supports_exact_comp_search']


def test_model_guesses_do_not_change_top5_order_or_money():
    rows = [listing(n, expected_resale=10) for n in range(8)] + [listing(20, MESSI, expected_resale=57)]
    before = build_best_alternatives(rows)
    inflated = deepcopy(rows)
    inflated[0]['expected_resale'] = 1_000_000
    inflated[-1]['expected_resale'] = 1
    after = build_best_alternatives(inflated)
    assert [r['url'] for r in before['rows']] == [r['url'] for r in after['rows']]
    assert before['rows'][0]['title'] == MESSI
    for row in after['rows']:
        assert row['market_value'] is None and row['practical_margin'] is None
        assert row['decision'] == 'UNDERSÖK'
    assert rows[-1]['expected_resale'] == 57


def test_late_low_serial_auto_survives_all_selection_stages_without_more_cpu_slots():
    rows = [listing(n, f'2023-24 Topps Chrome base card #{n}') for n in range(150)]
    rows += [listing(900, MESSI)]
    fast_pool = select_fast_analysis_pool(rows, cap=80)
    assert rows[-1] in fast_pool and len(fast_pool) == 80
    candidates = [(item, {'rank_score': 100 if item is not rows[-1] else 0,
                         'rookie_importance_matched': True}, {'score': 0}) for item in fast_pool]
    idx = next(n for n, row in enumerate(candidates) if row[0] is rows[-1])
    # Deliberately place the card beyond the score baseline.
    candidates.append(candidates.pop(idx))
    target = len(candidates) - 1
    adaptive = select_adaptive_full_analysis_indices(candidates, base_limit=12, hard_cap=28)
    diverse = diversify_full_analysis_indices(candidates, adaptive, base_limit=12, hard_cap=28, coverage_slots=16)
    final = merge_deep_analysis_routes(candidates, diverse, list(range(40)), hard_cap=28)
    assert target in adaptive and target in diverse and target in final
    assert len(final) == len(set(final)) == 28


def test_actual_app_shows_unknown_price_and_actionable_identity_checks():
    with patch('src.loader.load_data', return_value=[]), patch('importlib.reload', side_effect=lambda module: module):
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=30)
        app.session_state['results'] = [listing(n, MESSI if n == 0 else None, expected_resale=57) for n in range(9)]
        app.session_state['debug'] = {'price_research_funnel': {'opportunity_attached': 0}, 'total_items': 9}
        app.run()
        assert not app.exception
        table = next(frame.value for frame in app.dataframe if 'Bedömning' in frame.value.columns)
        assert len(table) == 5 and table['Prisindikation'].eq('Okänt').all()
        text = '\n'.join(str(element.value) for element in app.markdown)
        assert 'on-card-autograf' in text and 'Kontrollera före köp' in text
        assert 'Identifiera set/program, säsong/år, kortnummer' in text
