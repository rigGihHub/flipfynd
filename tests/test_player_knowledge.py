from datetime import date
from src.player_knowledge import get_player_knowledge, derive_lifecycle_context, knowledge_coverage
from src.player_market import load_player_market

def test_source_backed_player_knowledge_exists():
    k=get_player_knowledge("Connor Bedard","hockey")
    assert k["verified"] is True
    assert k["activity_status"]=="active"
    assert k["source_name"]=="NHL.com"

def test_unknown_player_stays_unknown():
    k=get_player_knowledge("Completely Unknown","hockey")
    assert k["verified"] is False
    life=derive_lifecycle_context(k,on_date=date(2026,9,11))
    assert life["stage"]=="unknown"
    assert life["derived"] is False

def test_young_active_lifecycle_is_derived_from_verified_facts():
    k=get_player_knowledge("Lamine Yamal","football")
    life=derive_lifecycle_context(k,on_date=date(2026,9,11))
    assert life["stage"]=="young_active"
    assert life["age"]==19

def test_retired_context():
    k=get_player_knowledge("Wayne Gretzky","hockey")
    life=derive_lifecycle_context(k,on_date=date(2026,9,11))
    assert life["stage"]=="retired"

def test_coverage_report_is_descriptive():
    out=knowledge_coverage(load_player_market())
    assert out["hockey"]["covered_players"] > 0
    assert out["football"]["covered_players"] > 0
    assert 0 <= out["hockey"]["coverage_pct"] <= 100
