import json
from pathlib import Path
from src.checklist_collectible_hierarchy import classify_collectible_signal, summarize_collectible_hierarchy
from src.card_market_knowledge import detect_market_knowledge_signals


def test_published_odds_beat_generic_chase_language():
    row={'label':'Clear Cut Young Guns','category':'rookie_parallel','rarity_signal':'chase','pull_odds':'1:144 Hobby','source_id':'u'}
    c=classify_collectible_signal(row)
    assert c['tier']=='published_odds_chase'
    assert c['rank']==4
    assert c['objective_scarcity'] is True


def test_numbered_parallel_is_not_called_case_hit():
    c=classify_collectible_signal({'label':'Red /25','category':'parallel','print_run':25,'source_id':'u'})
    assert c['tier']=='numbered_parallel'
    assert c['rank']==3


def test_manufacturer_chase_without_odds_stays_conservative():
    c=classify_collectible_signal({'label':'Budapest at Night','category':'chase_insert','rarity_signal':'manufacturer_chase','source_id':'t'})
    assert c['tier']=='manufacturer_chase'
    assert c['rank']==1
    assert c['objective_scarcity'] is False


def test_current_topps_chrome_2526_signals_are_source_backed():
    d=json.loads(Path('data/card_market_knowledge.json').read_text(encoding='utf-8'))
    source_ids={s['id'] for s in d['sources']}
    rows=[s for s in d['signals'] if s.get('product_family')=='Topps Chrome UEFA 2025-26']
    assert len(rows)>=4
    assert all(s.get('source_id') in source_ids for s in rows)
    assert any(s.get('label','').endswith('Budapest at Night') for s in rows)


def test_detection_exposes_collectible_hierarchy():
    hits=detect_market_knowledge_signals('2025-26 Topps Chrome UEFA Budapest at Night', 'football')
    assert hits
    hit=next(h for h in hits if h['label'].startswith('2025-26 Topps Chrome UCC Budapest at Night'))
    assert hit['collectible_hierarchy_tier']=='manufacturer_chase'
    assert 'knapphet' in hit['collectible_hierarchy_label'].lower()


def test_summary_prefers_objective_or_higher_structural_tier():
    result=summarize_collectible_hierarchy([
        {'label':'Generic chase','category':'chase_insert','rarity_signal':'manufacturer_chase','source_id':'t'},
        {'label':'Gold /10','category':'parallel','print_run':10,'source_id':'t'},
    ])
    assert result['top_tier']=='numbered_parallel'
    assert result['top_rank']==3
