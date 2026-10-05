from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from src.adaptive_deepening import select_adaptive_full_analysis_indices, merge_deep_analysis_routes
from src.best_alternatives import alternative_status, build_best_alternatives


def candidate(index, score, title=None):
    return ({'titel': title or f'Ordinary base {index}'}, {'rank_score': score}, {'score': 0})


def listing(index, **extra):
    return dict(titel=f'2023-24 Topps Chrome Lionel Messi #{index}',
                source_category='Fotboll', pris=16, frakt=29, analysis_total_cost=45,
                lank=f'https://www.tradera.com/item/293311/{index}/card', **extra)


def test_broader_score_band_admits_borderline_card_but_not_empty_tail():
    candidates = [candidate(n, 100) for n in range(12)]
    candidates += [candidate(12, 72), candidate(13, 10)]
    before = deepcopy(candidates)
    selected = select_adaptive_full_analysis_indices(candidates, base_limit=12, hard_cap=20)
    assert selected == list(range(13))
    assert candidates == before


def test_low_model_score_autograph_survives_full_score_and_price_route_pools():
    candidates = [candidate(n, 100 if n < 12 else 75) for n in range(80)]
    candidates.append(candidate(80, 0, 'Lionel Messi Superior Signatures Legends On-Card Auto /25 – 12/25'))
    selected = select_adaptive_full_analysis_indices(candidates, base_limit=12, hard_cap=28)
    assert 80 in selected
    merged = merge_deep_analysis_routes(candidates, selected, list(range(40)), hard_cap=28)
    assert 80 in merged
    assert len(merged) == len(set(merged)) == 28


@pytest.mark.parametrize('field', ['expected_resale', 'guide_price', 'guide_value', 'price_guide_value'])
@pytest.mark.parametrize('value', [10, 57, 500])
def test_model_only_estimate_cannot_reject_or_confirm_a_find(field, value):
    messi = listing(1, **{field: value})
    messi['titel'] = 'Lionel Messi Superior Signatures Legends On-Card Auto /25 – 12/25'
    original = deepcopy(messi)
    row = build_best_alternatives([messi])['rows'][0]
    assert row['decision'] == 'UNDERSÖK'
    assert row['practical_price_source'] == 'MODEL_GUIDE'
    assert row['market_value'] is None and row['sold_comps'] == 0
    assert row['heuristic_indication'] == value
    assert alternative_status(row).startswith('Potentiell kandidat')
    assert messi == original


def test_single_active_negative_remains_review_only_but_two_comps_reject_loss():
    rows = []
    for count in [1, 2]:
        rows.append(listing(count, asking_price_opportunity={
            'reference_asking_price': 20, 'net_margin': -30,
            'comparison_count': count, 'total_cost': 45}))
    result = build_best_alternatives(rows)['rows']
    single = next(row for row in result if row['asking_comparison_count'] == 1)
    two = next(row for row in result if row['asking_comparison_count'] == 2)
    assert single['decision'] == 'UNDERSÖK'
    assert alternative_status(single) == 'Osäkert · endast ett jämförelsepris'
    assert two['decision'] == 'AVSTÅ'
    assert alternative_status(two) == 'AVSTÅ · ingen positiv marginal'


def test_additional_candidates_are_bounded_unique_and_preserve_product_exclusions():
    rows = [listing(n, guide_price=10) for n in range(25)]
    rows += [dict(listing(100), titel='Panini Adrenalyn Messi /25 auto'),
             dict(listing(101), titel='Topps Match Attax Messi /25 auto')]
    original = deepcopy(rows)
    result = build_best_alternatives(rows)
    combined = result['rows'] + result['review_candidates']
    assert len(result['rows']) == 5 and len(result['review_candidates']) == 15
    assert len({row['url'] for row in combined}) == 20
    assert all(row['decision'] == 'UNDERSÖK' for row in combined)
    assert result['product_scope_excluded_count'] == 2
    assert result['available_count'] == 25
    assert rows == original


def test_confirmed_losses_do_not_fill_additional_potential_candidates():
    rows = [listing(n, asking_price_opportunity={
        'reference_asking_price': 20, 'net_margin': -30,
        'comparison_count': 2, 'total_cost': 45}) for n in range(10)]
    result = build_best_alternatives(rows)
    assert len(result['rows']) == 5
    assert result['review_candidates'] == []


def test_app_exposes_more_candidates_without_claiming_profit():
    rows = [listing(n, expected_resale=10) for n in range(9)]
    with patch('src.loader.load_data', return_value=[]), patch('importlib.reload', side_effect=lambda module: module):
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=30)
        app.session_state['results'] = rows
        app.session_state['debug'] = {'price_research_funnel': {'opportunity_attached': 0}, 'total_items': 9}
        app.run()
        assert not app.exception
        frame = next(frame.value for frame in app.dataframe if 'Bedömning' in frame.value.columns)
        assert len(frame) == 5
        assert frame['Bedömning'].str.startswith('Potentiell kandidat').all()
        assert frame['Netto / scenario'].eq('Ej beräkningsbar').all()
        assert any(expander.label == 'Fler potentiella kandidater (4)' for expander in app.expander)
