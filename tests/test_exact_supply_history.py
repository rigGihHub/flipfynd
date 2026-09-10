from pathlib import Path
from src.exact_supply_history import build_snapshot, load_history, save_snapshot, summarize_history

def target():
    return {
        "player_name":"Connor McDavid",
        "player_match_confidence":"high",
        "set_name":"Upper Deck",
        "season":"2015-16",
        "card_number":"201",
        "card_identity_confidence_score":90,
        "identity_evidence_sources":{"player_name":["a","b"]},
    }

def report(n):
    return {"ready":True,"confirmed_exact":n,"possible":1,"wrong_card":0}

def test_snapshot_is_factual_and_non_decisional():
    snap=build_snapshot(target(),report(2),observed_at="2026-09-01T10:00:00+00:00")
    assert snap["confirmed_exact"]==2
    assert snap["creates_value"] is False
    assert snap["creates_buy_decision"] is False

def test_history_needs_two_snapshots():
    snap=build_snapshot(target(),report(2),observed_at="2026-09-01T10:00:00+00:00")
    summary=summarize_history(target(),[snap])
    assert summary["status"]=="OTILLRÄCKLIG_HISTORIK"
    assert summary["direction"]=="EJ_BEDÖMBAR"

def test_history_detects_decrease():
    a=build_snapshot(target(),report(4),observed_at="2026-09-01T10:00:00+00:00")
    b=build_snapshot(target(),report(2),observed_at="2026-09-09T10:00:00+00:00")
    summary=summarize_history(target(),[a,b])
    assert summary["direction"]=="MINSKAT_OBSERVERAT_UTBUD"
    assert summary["change"]==-2

def test_save_and_load_roundtrip(tmp_path):
    p=tmp_path/"history.json"
    snap=build_snapshot(target(),report(3),observed_at="2026-09-01T10:00:00+00:00")
    assert save_snapshot(p,snap)==1
    rows=load_history(p)
    assert len(rows)==1
    assert rows[0]["confirmed_exact"]==3
    assert "creates_value" not in rows[0]

def test_history_is_identity_scoped():
    a=build_snapshot(target(),report(4),observed_at="2026-09-01T10:00:00+00:00")
    other=target(); other["card_number"]="202"
    b=build_snapshot(other,report(1),observed_at="2026-09-09T10:00:00+00:00")
    summary=summarize_history(target(),[a,b])
    assert summary["status"]=="OTILLRÄCKLIG_HISTORIK"
