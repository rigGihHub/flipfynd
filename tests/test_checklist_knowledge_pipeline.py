import json
from pathlib import Path
import pytest
from src.checklist_knowledge_pipeline import audit_knowledge, is_official_source_url, merge_knowledge


def test_official_source_allowlist():
    assert is_official_source_url('https://upperdeck.com/checklist/x')
    assert is_official_source_url('https://www.topps.com/pages/x')
    assert not is_official_source_url('https://random-marketplace.example/x')


def test_current_knowledge_has_no_structural_conflicts():
    d=json.loads(Path('data/card_market_knowledge.json').read_text(encoding='utf-8'))
    report=audit_knowledge(d)
    assert report['invalid_source_count'] == 0
    assert report['invalid_signal_count'] == 0
    assert report['conflict_count'] == 0


def test_pipeline_rejects_conflicting_print_run():
    base={
        'sources':[{'id':'u','publisher':'Upper Deck','url':'https://upperdeck.com/checklist/x'}],
        'signals':[{'sport':'hockey','label':'X Red','patterns':['x red'],'product_family':'X','program_family':'X Red','print_run':25,'source_id':'u'}],
    }
    with pytest.raises(ValueError):
        merge_knowledge(base, signals=[{'sport':'hockey','label':'X Red','patterns':['x red'],'product_family':'X','program_family':'X Red','print_run':99,'source_id':'u'}])


def test_series2_new_rarity_knowledge_is_source_backed():
    d=json.loads(Path('data/card_market_knowledge.json').read_text(encoding='utf-8'))
    by_label={x.get('label'):x for x in d['signals']}
    assert by_label['2025-26 Upper Deck Series 2 Incarnations']['pull_odds']=='1:1920 Hobby'
    assert by_label['2025-26 Upper Deck Series 2 Dazzlers Gold']['pull_odds']=='1:2880 Hobby'
    assert by_label['2025-26 Upper Deck Series 2 Population Count 25']['print_run']==25
