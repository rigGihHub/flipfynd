from copy import deepcopy

from src.seller_live_quick_analysis import quick_analyze_seller_inventory
from src.seller_live_full_analysis import full_analyze_live_seller_item
from src.seller_profit_display import build_seller_net_profit_summary
from src.seller_dynamic_top5 import preserve_dismissals, dismiss_seller_alternative
from src.seller_top5 import _fallback_row, _seller_alternative_rank_key
from tests.test_seller_dynamic_top5 import row, update, ids


def test_quick_analysis_keeps_negative_active_margin_through_fallback():
    scenario = {'net_margin': -45, 'possible_find': False}
    def analyze(item, **kwargs):
        return {'beslut': 'SKIP', 'asking_price_opportunity': scenario}
    quick = quick_analyze_seller_inventory({}, [row(1)['source_item']], analyze_fn=analyze)['rows'][0]
    fallback = _fallback_row(quick, 'seller')
    summary = build_seller_net_profit_summary(fallback)
    assert summary['available']
    assert summary['value'] == -45
    assert summary['evidence_kind'] == 'ACTIVE_ASKING'


def test_full_bridge_preserves_verified_source_and_alternative_profit_field():
    def analyze(item, **kwargs):
        return {'estimated_net_profit': -12, 'practical_price_source': 'VERIFIED'}
    full = full_analyze_live_seller_item(row(1)['source_item'], analyze_fn=analyze)
    assert full['estimated_net_profit'] == -12
    assert full['practical_price_source'] == 'VERIFIED'
    assert build_seller_net_profit_summary(full)['value'] == -12


def test_saved_compact_results_recover_missing_economics_from_source():
    saved = row(1, asking_price_opportunity=None)
    saved['source_item']['asking_price_opportunity'] = {'net_margin': -45}
    # An explicit compact None remains authoritative; missing fields recover.
    assert not build_seller_net_profit_summary(saved)['available']
    del saved['asking_price_opportunity']
    assert build_seller_net_profit_summary(saved)['value'] == -45


def test_explicit_unsafe_summary_does_not_recover_safe_source_valuation():
    saved = row(1, net_profit_estimate=0, valuation_display_safe=False)
    saved['source_item'].update(net_profit_estimate=100, valuation_display_safe=True)
    assert not build_seller_net_profit_summary(saved)['available']


def test_smallest_loss_precedes_hype_and_analysis_depth():
    small = row(1, score=1, net_profit_estimate=-2, valuation_display_safe=True)
    large = row(2, score=99, net_profit_estimate=-100, valuation_display_safe=True)
    assert _seller_alternative_rank_key(small) > _seller_alternative_rank_key(large)
    active = row(3, score=1, asking_price_opportunity={'net_margin': -1})
    active['analysis_level'] = 'quick_fallback'
    assert _seller_alternative_rank_key(active) > _seller_alternative_rank_key(small)
    _, selected = update(rows=[large, small, active])
    assert ids(selected) == ['3', '1', '2']


def test_known_positive_margins_compete_before_player_bonus():
    better = row(1, score=1, asking_price_opportunity={'possible_find': True, 'net_margin': 80})
    worse = row(2, score=99, asking_price_opportunity={'possible_find': True, 'net_margin': 2})
    better['analysis_level'] = 'quick_fallback'
    assert _seller_alternative_rank_key(better) > _seller_alternative_rank_key(worse)


def test_late_result_refills_five_after_preserving_removals():
    registry, alternatives = update(rows=[row(i, score=50-i) for i in range(8)])
    original = {'seller': 'seller', 'alternatives': alternatives, 'rows': [],
                'analysis_registry': registry, 'public_checkpoint': {'analysis_registry': registry}}
    worker = deepcopy(original)
    removed = dismiss_seller_alternative(original, '4')
    restored = preserve_dismissals(worker, removed)
    assert ids(restored['alternatives']) == ['0', '1', '2', '3', '5']
    assert restored['analysis_registry']['displayed_keys'] == ['0', '1', '2', '3', '5']
    assert restored['public_checkpoint']['analysis_registry']['displayed_keys'] == ['0', '1', '2', '3', '5']
    assert ids(worker['alternatives']) == ['0', '1', '2', '3', '4']


def test_ui_distinguishes_active_loss_from_sold_backed_loss():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    active = row(0, asking_price_opportunity={'net_margin': -1})
    sold = row(1, net_profit_estimate=-2, valuation_display_safe=True)
    registry, alternatives = update(rows=[active, sold, row(2), row(3), row(4)])
    app = AppTest.from_file(str(Path('app.py').resolve()), default_timeout=30)
    app.session_state['seller_top5_result'] = {
        'status': 'INVENTORY_PARTIAL', 'seller': 'test', 'inventory_count': 5,
        'alternatives': alternatives, 'rows': [], 'analysis_registry': registry,
    }
    app.run()
    assert not app.exception
    rendered = '\n'.join(element.value for element in app.markdown)
    assert 'Negativ marginal mot begärda priser · osäkert scenario' in rendered
    assert 'Avstå · negativ beräknad nettovinst' in rendered
    assert 'Nettoscenario mot begärda priser: -1 kr' in rendered
    assert 'Nettovinst efter kostnader: -2 kr' in rendered
    assert 'KÖP · verifierat fynd' not in rendered
