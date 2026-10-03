from datetime import datetime, timedelta, timezone
import pytest
from src.player_interest import player_interest, row_player
from src.player_form_monitor import football_events, hockey_events, collect_form

NOW = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)

def event(name='Connor McDavid', age=0, **extra):
    return dict(player_name=name, sport='hockey', event_type='performance_breakout',
                occurred_at=(NOW-timedelta(days=age)).isoformat(), source_name='NHL',
                source_url=f'https://api-web.nhle.com/game/{age}', detail='3 poäng', **extra)


def test_recent_performance_decays_and_cannot_be_revived_by_observation_time():
    assert player_interest('Connor McDavid', events=[event()], now=NOW)['form_bonus'] == 12
    assert player_interest('Connor McDavid', events=[event(age=7)], now=NOW)['form_bonus'] == 6
    assert player_interest('Connor McDavid', events=[event(age=14, observed_at=NOW.isoformat())], now=NOW)['form_bonus'] == 0
    assert player_interest('Connor McDavid', events=[event(age=-1)], now=NOW)['form_bonus'] == 0


def test_no_evidence_no_form_aliases_sport_and_duplicate_protection():
    assert player_interest('Unknown Player', events=[], now=NOW)['ranking_bonus'] == 0
    assert player_interest('Connor McDavid', events=[event(),event()], now=NOW)['form_bonus'] == 12
    assert player_interest('Connor Mcdavid', events=[event()], now=NOW)['form_bonus'] == 12
    wrong = event(); wrong['sport'] = 'football'
    assert player_interest('Connor McDavid', 'hockey', events=[wrong], now=NOW)['form_bonus'] == 0


@pytest.mark.parametrize('name,sport', [('Wayne Gretzky','hockey'),('Peter Forsberg','hockey'),('Sidney Crosby','hockey'),('Lionel Messi','football'),('Ronaldinho','football')])
def test_legends_keep_substantial_bonus_without_recent_performance(name, sport):
    interest = player_interest(name, sport, events=[], now=NOW)
    assert interest['legend_bonus'] == 20
    assert interest['ranking_bonus'] == 20
    assert interest['legacy_source']['source_name']


def test_form_and_legend_are_bounded_and_repeated_form_is_capped():
    assert player_interest('Connor McDavid', events=[event(age=i) for i in range(8)], now=NOW)['form_bonus'] == 18
    hot_legend = event('Sidney Crosby')
    assert player_interest('Sidney Crosby', events=[hot_legend], now=NOW)['ranking_bonus'] == 30


def test_football_only_final_goals_not_assists_own_goals_or_shootouts():
    play = {'scoringPlay':True,'athletesInvolved':[{'displayName':'Erling Haaland'}]}
    comp = {'status':{'type':{'completed':True}},'details':[play,play,dict(play,ownGoal=True),dict(play,shootout=True)]}
    data = {'events':[{'date':NOW.isoformat(),'competitions':[comp]}]}
    result = football_events(data,'https://site.api.espn.com/scoreboard')
    assert len(result) == 1 and result[0]['metric_after'] == 2
    comp['status']['type']['completed'] = False
    assert not football_events(data,'url')


def test_nhl_requires_full_identity_completed_non_preseason_match():
    box={'id':1,'startTimeUTC':NOW.isoformat(),'gameState':'OFF','gameType':2,
         'playerByGameStats':{'homeTeam':{'forwards':[{'playerId':7,'goals':1,'points':3}]}}}
    assert hockey_events(box,{}) == []
    assert hockey_events(box,{7:'Connor McDavid'})[0]['player_name'] == 'Connor McDavid'
    assert hockey_events(dict(box,gameType=1),{7:'Connor McDavid'}) == []
    assert hockey_events(dict(box,gameState='LIVE'),{7:'Connor McDavid'}) == []


def test_partial_source_outage_retains_only_recent_existing_evidence():
    import requests
    def get(url):
        if 'eng.1' in url:
            return {'events':[]}
        raise requests.Timeout('offline')
    result = collect_form({'events':[event(age=2),event(age=16)]}, now=NOW, get=get)
    assert len(result['events']) == 1
    assert sum(s['ok'] for s in result['sources']) == 4
    assert result['checked_at'] == NOW.isoformat()


def test_interest_does_not_mutate_economics_and_promotes_legend_among_peers():
    from src.seller_top5 import _refresh_collector_research, _seller_alternative_rank_key
    common = dict(price=20, rank_score=40, deal_score=30, analysis_level='full',
                  sold_comps=0, decision='SKIP', net_profit_estimate=-10, max_price=5)
    ordinary = dict(common,title='2023 Upper Deck Connor McDavid #1')
    legend = dict(common,title='2023 Upper Deck Peter Forsberg #1')
    refreshed = _refresh_collector_research(legend)
    assert refreshed['net_profit_estimate'] == -10 and refreshed['max_price'] == 5
    assert refreshed['decision'] == 'SKIP'
    assert _seller_alternative_rank_key(legend) > _seller_alternative_rank_key(ordinary)


def test_cached_feed_refreshes_when_the_file_changes(tmp_path, monkeypatch):
    import json
    import src.player_interest as interest
    monkeypatch.setattr(interest, 'DATA_DIR', tmp_path)
    (tmp_path/'player_form.json').write_text(json.dumps({'events':[]}))
    assert interest._load('player_form.json')['events'] == []
    (tmp_path/'player_form.json').write_text(json.dumps({'events':[event()]}))
    assert len(interest._load('player_form.json')['events']) == 1
    interest._read_data.cache_clear()
    interest._cached_row_interest.cache_clear()


def test_interest_is_weighted_once_in_seller_opportunity_score():
    from src.seller_top5 import _seller_opportunity_score
    common = {'title':'2023 Upper Deck Peter Forsberg #1','deal_score':30, 'rank_score':40}
    analyzed = dict(common,rank_score=48,source_item={'player_interest':{'applied_rank_bonus':8}})
    assert _seller_opportunity_score(analyzed) == _seller_opportunity_score(common)


def test_negative_legend_does_not_outrank_verified_positive_economics():
    from src.seller_top5 import _seller_alternative_rank_key
    positive = {'title':'Ordinary profitable card','decision':'UNDERSÖK','identity_ok':True,
                'exact_identity_gate_supports_exact_comp_search':True,'sold_comps':2,
                'valuation_confidence':70,'risk_score':20,'net_profit_estimate':10,
                'risk_adjusted_profit':10,'valuation_display_safe':True,'analysis_level':'full'}
    legend = dict(positive,title='2023 Upper Deck Wayne Gretzky #1',net_profit_estimate=-10,
                  risk_adjusted_profit=-10,rank_score=100,deal_score=100)
    assert _seller_alternative_rank_key(positive) > _seller_alternative_rank_key(legend)
