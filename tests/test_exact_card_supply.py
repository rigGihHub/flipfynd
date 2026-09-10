from src.exact_card_supply import (
    build_exact_supply_query,
    count_analyzed_exact_matches,
    verify_exact_query_supply,
)

def exact_item():
    return {
        "player_name":"Connor McDavid",
        "player_match_confidence":"high",
        "set_name":"Upper Deck",
        "season":"2015-16",
        "card_number":"201",
        "card_identity_confidence_score":90,
        "identity_evidence_sources":{"player_name":["a","b"]},
    }

def test_query_requires_exact_identity_gate():
    bad={"player_name":"Connor McDavid"}
    out=build_exact_supply_query(bad)
    assert out["ready"] is False
    assert out["query"] is None

def test_query_uses_only_structured_identity():
    out=build_exact_supply_query(exact_item())
    assert out["ready"] is True
    assert out["query"]=="Connor McDavid Upper Deck 2015-16 201"

def test_optional_parallel_is_used_when_structured():
    item=exact_item()
    item["parallel"]="Silver Foil"
    out=build_exact_supply_query(item)
    assert out["query"].endswith("Silver Foil")

def test_local_exact_match_count_requires_same_exact_identity():
    a=exact_item(); a["tradera_item_id"]="1"
    b=exact_item(); b["tradera_item_id"]="2"
    c=exact_item(); c["card_number"]="202"; c["tradera_item_id"]="3"
    out=count_analyzed_exact_matches(a,[a,b,c])
    assert out["exact_analyzed_matches"]==2
    assert out["creates_buy_decision"] is False
    assert out["creates_value"] is False

def test_api_hits_are_candidates_not_exact_claims(monkeypatch):
    def fake(**kwargs):
        return {"ok":True,"status":"OK","items":[{"tradera_item_id":"1"},{"tradera_item_id":"1"},{"tradera_item_id":"2"}]}
    monkeypatch.setattr("src.exact_card_supply.search_once",fake)
    out=verify_exact_query_supply(exact_item(),app_id="1",app_key="k",category_name="Hockey - NHL",pages=2)
    assert out["observed_query_candidates"]==2
    assert "inte bekräftade" in out["scope_note"]
    assert out["creates_buy_decision"] is False
    assert out["creates_value"] is False
