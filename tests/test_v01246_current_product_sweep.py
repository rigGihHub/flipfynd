import json
from pathlib import Path
from src.card_market_knowledge import detect_market_knowledge_signals
from src.checklist_collectible_hierarchy import classify_collectible_signal


def test_common_published_odds_are_not_promoted_to_rare_chase():
    c = classify_collectible_signal({
        'label':'Young Guns base', 'category':'rookie_program',
        'pull_odds':'1:2 Hobby', 'source_id':'ud'
    })
    assert c['tier'] == 'published_frequency'
    assert c['rank'] == 2
    assert c['objective_scarcity'] is False


def test_rare_published_odds_still_rank_as_chase():
    c = classify_collectible_signal({
        'label':'Clear Cut Young Guns', 'category':'rookie_parallel',
        'pull_odds':'1:144 Hobby', 'source_id':'ud'
    })
    assert c['tier'] == 'published_odds_chase'
    assert c['objective_scarcity'] is True


def test_current_opc_platinum_emerald_surge_is_exactly_numbered():
    hits = detect_market_knowledge_signals('2025-26 O-Pee-Chee Platinum Marquee Rookies Emerald Surge', 'hockey')
    hit = next(h for h in hits if h['label'].endswith('Emerald Surge /10'))
    assert hit['print_run'] == 10
    assert hit['collectible_hierarchy_tier'] == 'numbered_parallel'


def test_current_metal_pmg_blue_is_known_numbered_structure():
    hits = detect_market_knowledge_signals('2025-26 Skybox Metal Universe PMG Blue rookie', 'hockey')
    hit = next(h for h in hits if 'PMG Blue' in h['label'])
    assert hit['print_run'] == 50


def test_current_finest_variation_stays_conservative_without_odds():
    hits = detect_market_knowledge_signals('2025-26 Topps Finest UEFA HoloGlow Variation', 'football')
    hit = next(h for h in hits if 'HoloGlow' in h['label'])
    assert hit['collectible_hierarchy_tier'] == 'manufacturer_chase'
    assert hit['collectible_hierarchy_rank'] == 1


def test_new_sources_are_official_and_present():
    d = json.loads(Path('data/card_market_knowledge.json').read_text(encoding='utf-8'))
    ids = {s['id'] for s in d['sources']}
    assert {'ud_opc_platinum_2526','ud_metal_2526','topps_finest_ucc_2526'} <= ids
