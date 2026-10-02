from src import seller_top5 as top
from src.seller_analysis_registry import normalize_registry
from src.seller_dynamic_top5 import update_dynamic_top5


def row(i, score=10, **extra):
    source = {'tradera_item_id': str(i), 'titel': f'2023-24 Upper Deck Hockey Player {i} #{i}',
              'lank': f'https://www.tradera.com/item/293316/{i}', 'pris': 20}
    return dict(title=source['titel'], url=source['lank'], price=20, source_item=source,
                decision='SKIP', rank_score=score, analysis_level='full', **extra)


def update(registry=None, rows=(), quick=(), inventory=None):
    return update_dynamic_top5(
        registry, inventory=inventory or [row(i)['source_item'] for i in range(20)],
        quick_rows=quick, full_rows=rows, seed_rows=[],
        rank_key=top._seller_alternative_rank_key, refresh=top._refresh_collector_research,
        quick_fallback=lambda q: top._fallback_row(q, 'seller'), select_diverse=top._select_diverse_rows)


def ids(rows):
    return [r['source_item']['tradera_item_id'] for r in rows]


def test_five_uncertain_alternatives_remain_visible_and_only_better_new_cards_enter():
    original = [row(i, score=50-i) for i in range(5)]
    assert all(top.seller_result_tier(r) == 'WEAK' for r in original)
    registry, first = update(rows=original)
    assert ids(first) == ['0', '1', '2', '3', '4']
    # Simulate a checkpoint serialization/restore between rounds.
    registry, weaker = update(normalize_registry(registry), rows=[row(5, score=1)])
    assert ids(weaker) == ids(first)
    registry, improved = update(registry, rows=[row(6, score=100)])
    assert ids(improved) == ['6', '0', '1', '2', '3']
    assert all(r['seller_top5_alternative'] for r in improved)
    _, tied = update(registry, rows=[row(7, score=47)])
    assert ids(tied) == ids(improved)


def test_full_loss_supersedes_old_fast_candidate_and_never_becomes_find():
    fast = row(1, score=99)
    fast['analysis_level'] = 'quick_fallback'
    registry, _ = update(rows=[fast, row(2, score=1)])
    loss = row(1, score=100, net_profit_estimate=-30, valuation_display_safe=True)
    registry, selected = update(registry, rows=[loss], quick=[fast])
    assert ids(selected) == ['2', '1']
    assert selected[1]['analysis_level'] == 'full'
    assert top.seller_result_tier(selected[1]) == 'WEAK'
    registry['entries']['1'] = {'full_count': 1}
    _, later = update(registry, quick=[fast])
    assert later[1]['net_profit_estimate'] == -30


def test_price_failure_or_removed_listing_replaces_old_result_without_dummy_slots():
    registry, _ = update(rows=[row(i) for i in range(6)])
    invalid = row(0)
    invalid['price'] = 0
    _, selected = update(registry, rows=[invalid], inventory=[row(i)['source_item'] for i in range(5)])
    assert ids(selected) == ['1', '2', '3', '4']


def test_duplicate_cards_can_fill_available_five_listing_slots():
    rows = [row(i) for i in range(6)]
    for r in rows:
        r['source_item']['titel'] = r['title'] = '2023-24 Upper Deck Young Guns #201 Connor Bedard'
    _, selected = update(rows=rows)
    assert len(selected) == 5
    assert len(set(ids(selected))) == 5


def test_build_returns_five_alternatives_even_when_find_gate_rejects_all():
    inventory = [row(i)['source_item'] for i in range(12)]
    def analyze(item, **kwargs):
        return {'beslut': 'SKIP', 'rank_score': 5, 'sold_comparable_count': 0}
    out = top.build_seller_top5('seller', inventory, analyze_fn=analyze)
    assert out['rows'] == []
    assert len(out['alternatives']) == 5
    assert len(out['analysis_registry']['alternative_rows']) >= 5
    assert out['top5_new_count'] == 5


def test_streamlit_renders_all_five_uncertain_alternatives_with_loss_warning():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    registry, alternatives = update(rows=[row(i) for i in range(5)])
    alternatives[-1]['net_profit_estimate'] = -30
    alternatives[-1]['valuation_display_safe'] = True
    app = AppTest.from_file(str(Path('app.py').resolve()), default_timeout=30)
    app.session_state['seller_top5_result'] = {
        'status': 'INVENTORY_PARTIAL', 'seller': 'test', 'inventory_count': 5,
        'alternatives': alternatives, 'rows': [], 'analysis_registry': registry,
    }
    app.run()
    assert not app.exception
    rendered = '\n'.join(element.value for element in app.markdown)
    for position, alternative in enumerate(alternatives, 1):
        assert f"#{position} · {alternative['title']}" in rendered
    assert 'Avstå · negativ beräknad nettovinst' in rendered
    assert 'Nettovinst efter kostnader: -30 kr' in rendered
    assert 'Topp 5 hittills' in rendered
    assert 'KÖP · verifierat fynd' not in rendered


def test_removing_fifth_promotes_sixth_and_stays_removed_after_new_analysis():
    from src.seller_dynamic_top5 import dismiss_seller_alternative
    registry, alternatives = update(rows=[row(i, score=50-i) for i in range(7)])
    original = {'seller': 'seller', 'inventory_count': 7, 'alternatives': alternatives,
                'analysis_registry': registry, 'analysis_round': 4, 'full_unique_analysed': 7,
                'public_checkpoint': {'next_page': 4, 'items': {}, 'analysis_registry': registry}}
    removed = dismiss_seller_alternative(original, '4')
    assert ids(removed['alternatives']) == ['0', '1', '2', '3', '5']
    assert ids(original['alternatives']) == ['0', '1', '2', '3', '4']
    assert removed['analysis_round'] == 4
    assert removed['full_unique_analysed'] == 7
    assert removed['public_checkpoint']['analysis_registry']['dismissed_keys'] == ['4']
    registry, later = update(normalize_registry(removed['analysis_registry']), rows=[row(4, score=100)])
    assert '4' not in ids(later)
    assert len(later) == 5
    twice = dismiss_seller_alternative(dict(removed, analysis_registry=registry, alternatives=later), '0')
    assert ids(twice['alternatives']) == ['1', '2', '3', '5', '6']


def test_removing_last_available_candidate_never_invents_a_replacement():
    from src.seller_dynamic_top5 import dismiss_seller_alternative
    registry, alternatives = update(rows=[row(1)])
    removed = dismiss_seller_alternative({'alternatives': alternatives, 'analysis_registry': registry}, '1')
    assert removed['alternatives'] == []
    assert removed['analysis_registry']['dismissed_keys'] == ['1']


def test_streamlit_remove_button_promotes_sixth_without_a_search():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    registry, alternatives = update(rows=[row(i, score=50-i) for i in range(6)])
    app = AppTest.from_file(str(Path('app.py').resolve()), default_timeout=30)
    app.session_state['seller_top5_result'] = {
        'status': 'INVENTORY_PARTIAL', 'seller': 'test', 'inventory_count': 6,
        'alternatives': alternatives, 'rows': [], 'analysis_registry': registry,
        'full_unique_analysed': 6,
    }
    app.run()
    app.button(key='seller_remove_4').click().run()
    assert not app.exception
    result = app.session_state['seller_top5_result']
    assert ids(result['alternatives']) == ['0', '1', '2', '3', '5']
    assert result['full_unique_analysed'] == 6
    rendered = '\n'.join(element.value for element in app.markdown)
    assert '#5 · ' + row(5)['title'] in rendered
    assert row(4)['title'] not in rendered
