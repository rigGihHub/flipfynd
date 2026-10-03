from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from src.best_alternatives import build_best_alternatives, alternative_status


def listing(index, margin=None):
    row = {'titel': f'2020-21 Upper Deck #12 Player {index}',
           'lank': f'https://www.tradera.com/item/293316/{index}/card',
           'pris': 60, 'frakt': 30, 'analysis_total_cost': 95, 'beslut': 'SKIP'}
    if margin is not None:
        row['asking_price_opportunity'] = {
            'status': 'POSSIBLE_FIND' if margin > 0 else 'NO_EDGE',
            'possible_find': margin > 0, 'net_margin': margin,
            'reference_asking_price': 150, 'comparison_count': 2,
            'total_cost': 95, 'purchase_price': 60, 'shipping': 30}
    return row


def test_fills_five_with_honest_losses_and_preserves_input():
    rows = [listing(i, -i) for i in range(1, 8)]
    result = build_best_alternatives(rows)['rows']
    assert len(result) == 5
    assert [row['asking_net_margin'] for row in result] == [-1, -2, -3, -4, -5]
    assert all(row['decision'] == 'AVSTÅ' and row['market_value'] is None for row in result)
    assert all(row['beslut'] == 'SKIP' for row in rows)


def test_finds_and_unknowns_precede_loss_fillers_and_tiny_margin_stays_weak():
    rows = [listing(1, 65), listing(2, 2), listing(3), listing(4, -5), listing(5, -1), listing(6, -10)]
    result = build_best_alternatives(rows)['rows']
    assert [row['_source_item']['titel'] for row in result][:3] == [row['titel'] for row in rows[:3]]
    assert len(result) == 5
    assert alternative_status(result[1]) == 'Svag marginal · inget fynd'
    assert all(row['decision'] != 'KÖP' for row in result)


def test_single_comparison_research_lead_joins_main_five_without_buy_promotion():
    lead = {'title': '2020-21 Upper Deck Bobby Orr #CM-5',
            'url': 'https://www.tradera.com/item/293316/999/orr',
            'scenario': {'status': 'RESEARCH_SINGLE_ACTIVE', 'net_margin': 119,
                         'reference_asking_price': 282, 'comparison_count': 1,
                         'total_cost': 94}}
    result = build_best_alternatives([listing(i, -i) for i in range(1, 6)], research_leads=[lead])['rows']
    assert len(result) == 5
    assert result[0]['title'] == lead['title']
    assert result[0]['total_cost'] == 94
    assert alternative_status(result[0]) == 'Osäkert · endast ett jämförelsepris'
    assert result[0]['market_value'] is None and result[0]['sold_comps'] == 0


def test_duplicate_links_and_short_inventory_are_not_fabricated():
    row = listing(1, -5)
    duplicate = dict(row, lank=row['lank'] + '?ref=duplicate')
    result = build_best_alternatives([row, duplicate, listing(2)])
    assert result['available_count'] == len(result['rows']) == 2
    assert build_best_alternatives([])['rows'] == []


def test_verified_buy_remains_first_even_with_many_larger_asking_scenarios():
    verified = dict(listing(10), beslut='KÖP', valuation_display_safe=True,
                    market_value=200, sold_comparable_count=3, net_profit_estimate=60)
    result = build_best_alternatives([listing(i, 200 + i) for i in range(1, 8)] + [verified])['rows']
    assert len(result) == 5
    assert result[0]['decision'] == 'KÖP'
    assert result[0]['title'] == verified['titel']
    assert all(row['decision'] == 'UNDERSÖK' for row in result[1:])


@pytest.mark.parametrize('advanced', [False, True])
def test_app_shows_five_even_when_all_candidates_lose_money(advanced):
    rows = [listing(i, -i) for i in range(1, 8)]
    with patch('src.loader.load_data', return_value=[]), patch('importlib.reload', side_effect=lambda module: module):
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=30)
        app.session_state['results'] = rows
        app.session_state['show_advanced_terminal'] = advanced
        app.session_state['debug'] = {'price_research_funnel': {'opportunity_attached': 7}, 'total_items': 7}
        app.run()
        assert not app.exception
        table = next(frame.value for frame in app.dataframe if 'Bedömning' in frame.value.columns)
        assert len(table) == 5
        assert table['Bedömning'].str.startswith('AVSTÅ').all()
        assert any('De 5 bästa alternativen' in value.value for value in app.markdown)
