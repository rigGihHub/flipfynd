"""Observed Cardland title plus large-profile routing regressions."""
from src.card_parser import parse_card_features, has_relic_material_evidence
from src.seller_collector_signals import collector_signals
from src.seller_top5 import (_refresh_collector_research, seller_result_tier,
                             _select_deep_route_candidates)
from src.seller_analysis_registry import begin_run, merge_best_rows

CARDLAND_TITLE = '2019-20 Synergy Rookie Journey Away Jersey #RP4 Ryan Poehling UER (12-KK6-NHLCAN'


def test_observed_cardland_title_routes_to_actual_player_and_product():
    parsed = parse_card_features(CARDLAND_TITLE)
    assert parsed['player_name'] == 'Ryan Poehling'
    assert parsed['set_name'] == 'Synergy'
    assert parsed['card_number'] == 'RP4'
    assert parsed['is_jersey'] is False
    assert 'patch_relic' not in collector_signals({'titel': CARDLAND_TITLE})['signals']


def test_team_photo_and_product_names_do_not_invent_material_evidence():
    for title in (CARDLAND_TITLE,
                  '2021-22 Artifacts Dawson Mercer Rookie /999 #RED-198. New Jersey',
                  '2022-23 UD SP Game Used Nick Abruzzese Rookie Purity #P-81. Toronto',
                  '2023-24 Synergy Rookie Journey Home Jersey #RP4 Player Name'):
        assert not has_relic_material_evidence(title)
        assert not parse_card_features(title)['is_game_worn']
    # Real material wording still routes to research, even with the same labels.
    for title in ('SP Game Used Rookie Authentic Game-Worn Jersey',
                  'Synergy Rookie Journey Away Jersey Patch Auto',
                  'New Jersey Devils Nico Hischier Game-Used Jersey'):
        assert has_relic_material_evidence(title)


def test_saved_false_material_highlight_is_revalidated_and_evicted():
    old = {'price': 14, 'decision': 'SKIP', 'title': CARDLAND_TITLE,
           'source_item': {'tradera_item_id': '685706640', 'titel': CARDLAND_TITLE, 'pris': 14},
           'collector_signal_score': 19, 'collector_signals': ['rookie', 'patch_relic']}
    refreshed = _refresh_collector_research(old)
    assert refreshed['collector_signals'] == ['rookie']
    assert seller_result_tier(refreshed) == 'WEAK'
    registry = begin_run(None)
    registry['best_rows'] = {'685706640': refreshed}
    _, rows = merge_best_rows(registry, [], rank_key=lambda row: 1,
                              presentable=lambda row: seller_result_tier(row) != 'WEAK')
    assert rows == []


def _row(i, title):
    return {'source_item': {'tradera_item_id': str(i), 'titel': title}, 'title': title}


def test_cheap_price_probes_cannot_crowd_out_merit_or_exploration():
    asking = [_row(i, f'Generic card {i}') for i in range(40)]
    merit = [_row(100+i, f'Rare card {i}') for i in range(40)]
    exploration = [_row(200+i, f'Hidden card {i}') for i in range(4)]
    selected = _select_deep_route_candidates(merit, asking, exploration,
                                             registry=begin_run(None), budget=30)
    ids = [int(row['source_item']['tradera_item_id']) for row in selected]
    assert len(ids) == 30
    assert sum(100 <= i < 200 for i in ids) >= 16
    assert sum(i < 100 for i in ids) >= 8
    assert sum(i >= 200 for i in ids) == 4


def test_duplicate_listing_of_exact_card_spends_only_one_deep_slot():
    title = '2023-24 Upper Deck #451 Connor Bedard Young Guns'
    copies = [_row(i, title) for i in range(30)]
    other = _row(100, '2022-23 Upper Deck #201 Matty Beniers Young Guns')
    selected = _select_deep_route_candidates(copies + [other], copies, [],
                                             registry=begin_run(None), budget=30)
    assert len(selected) == 2


def test_price_router_does_not_reward_away_jersey_as_material(monkeypatch):
    from src import asking_price_opportunity as asking
    monkeypatch.setattr(asking, 'configured_credentials', lambda: ('id', 'secret'))
    plain = {'source_item': {'titel': '2019-20 Synergy #RP4 Ryan Poehling', 'pris': 1, 'frakt': 0}}
    false_relic = {'source_item': {'titel': CARDLAND_TITLE, 'pris': 14, 'frakt': 0}}
    routed = asking.select_asking_price_research([plain, false_relic])
    assert routed[0]['source_item'] == plain['source_item']
