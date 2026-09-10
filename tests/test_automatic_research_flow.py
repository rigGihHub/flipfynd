from src.automatic_research_flow import build_automatic_research_flow

def base():
    return {"player_name":"A","player_match_confidence":"high","decision":"BEVAKA"}

def test_local_checks_are_automatic():
    out=build_automatic_research_flow(base(),[],[])
    assert len(out["auto_completed"]) >= 5
    assert out["creates_buy_decision"] is False
    assert out["creates_value"] is False

def test_identity_gaps_collapse_to_one_human_intervention():
    out=build_automatic_research_flow(base(),[],[])
    nxt=out["next_intervention"]
    assert nxt["type"]=="HUMAN_VERIFICATION"
    assert nxt["label"]=="Verifiera kortidentiteten"
    assert len(nxt["actions"]) >= 1

def test_external_research_only_after_identity_is_ready():
    item={
        "player_name":"Connor McDavid",
        "player_match_confidence":"high",
        "set_name":"Upper Deck",
        "season":"2015-16",
        "card_number":"201",
        "card_identity_confidence_score":90,
        "identity_evidence_sources":{"player_name":["a","b"]},
        "decision":"BEVAKA",
        "sold_comparable_count":0,
    }
    out=build_automatic_research_flow(item,[],[])
    assert out["next_intervention"]["type"]=="EXTERNAL_RESEARCH"
    assert out["next_intervention"]["label"].startswith("Hitta")
