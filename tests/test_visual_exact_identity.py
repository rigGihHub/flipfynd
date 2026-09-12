from src.visual_exact_identity import resolve_visual_exact_identity


def finding(**overrides):
    d={
        'player_name':'Connor Bedard',
        'set_or_product':'Upper Deck Series 2',
        'season_or_year':'2023-24',
        'card_number':'451',
        'parallel_or_variant':'Young Guns Outburst Red',
        'serial_numerator':7,
        'serial_denominator':25,
        'rookie_marker_visible':'yes',
        'autograph_visible':'no',
        'relic_or_patch_visible':'no',
        'visual_clues':['Young Guns','Outburst Red'],
        'overall_confidence':0.91,
    }
    d.update(overrides)
    return d


def test_visual_exact_identity_ranks_verified_observed_candidate():
    sold=[{
        'player_name':'Connor Bedard','set_name':'Upper Deck Series 2','season':'2023-24',
        'card_number':'451','parallel':'Young Guns Outburst Red','serial_denominator':25,
        'is_rookie':True,'sold_price':4200,'sale_date':'2026-08-01','platform':'sold source',
        'url':'https://example.test/sold','verified_sold':True,'status':'sold',
    }]
    r=resolve_visual_exact_identity(finding(), observed_records=sold, sport='hockey')
    assert r['best_candidate']
    assert r['best_candidate']['combined_score'] >= 70
    assert 'Connor Bedard' in r['best_candidate']['label']


def test_checklist_conflict_blocks_exact_readiness():
    r=resolve_visual_exact_identity(finding(serial_denominator=99), observed_records=[], sport='hockey')
    assert not r['exact_identity_ready']
    assert any('konflikt' in x.casefold() or 'motsäg' in x.casefold() for x in r['blockers'] + r['next_actions'])


def test_missing_card_number_requests_back_scan_verification():
    r=resolve_visual_exact_identity(finding(card_number=None), observed_records=[], sport='hockey')
    assert any('kortnummer' in x.casefold() for x in r['next_actions'])
