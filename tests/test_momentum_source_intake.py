from src.momentum_source_intake import ingest_momentum_records
from src.momentum_source_registry import source_registry
from src.momentum_card_bridge import bridge_momentum_to_cards

def rec():
    return {"player_name":"A","sport":"hockey","event_type":"ranking_rise",
            "source_name":"NHL","source_url":"https://example.com","source_type":"official_league",
            "occurred_at":"2026-09-01T00:00:00Z"}

def test_intake_accepts_attributed_structured_record():
    r=ingest_momentum_records([rec()])
    assert r["accepted_count"]==1 and r["rejected_count"]==0

def test_intake_rejects_unsupported_source_type():
    x=rec(); x["source_type"]="random_social_post"
    r=ingest_momentum_records([x])
    assert r["accepted_count"]==0 and r["rejected"][0]["reason"]=="unsupported_source_type"

def test_intake_never_claims_scraping():
    assert ingest_momentum_records([rec()])["automated_scraping_used"] is False

def test_registry_does_not_claim_connections():
    r=source_registry()
    assert r["connected_count"]==0
    assert all(x["automated_ingestion"] is False for x in r["sources"])

def test_bridge_matches_exact_normalized_player_name():
    w={"players":[{"player_name":"A","event_count":2,"source_count":2}]}
    c=[{"player_name":"A","titel":"Card","decision":"BEVAKA","lank":"x"}]
    r=bridge_momentum_to_cards(w,c)
    assert len(r["matches"])==1 and r["matches"][0]["existing_decision"]=="BEVAKA"

def test_bridge_does_not_upgrade_decision():
    w={"players":[{"player_name":"A","event_count":2,"source_count":2}]}
    r=bridge_momentum_to_cards(w,[{"player_name":"A","decision":"BEVAKA"}])
    x=r["matches"][0]
    assert x["decision_changed"] is False and x["valuation_changed"] is False and x["max_bid_changed"] is False

def test_bridge_does_not_guess_player_from_title():
    w={"players":[{"player_name":"A","event_count":2,"source_count":2}]}
    r=bridge_momentum_to_cards(w,[{"titel":"A Young Guns"}])
    assert r["status"]=="NO_MATCHES"
