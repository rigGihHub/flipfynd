from src.exact_supply_confirmation import classify_candidate_against_target, build_confirmation_report

def base_item():
    return {
        "player_name":"Connor McDavid",
        "player_match_confidence":"high",
        "set_name":"Upper Deck",
        "season":"2015-16",
        "card_number":"201",
        "card_identity_confidence_score":90,
        "identity_evidence_sources":{"player_name":["a","b"]},
    }

def test_confirmed_exact_requires_candidate_exact_gate():
    target=base_item()
    cand=base_item()
    out=classify_candidate_against_target(target,cand)
    assert out["status"]=="CONFIRMED_EXACT"
    assert out["exact_match"] is True
    assert out["creates_buy_decision"] is False

def test_explicit_card_number_mismatch_is_wrong_card():
    target=base_item()
    cand=base_item(); cand["card_number"]="202"
    out=classify_candidate_against_target(target,cand)
    assert out["status"]=="WRONG_CARD"
    assert "card_number" in out["mismatch_fields"]

def test_missing_identity_is_possible_not_exact():
    target=base_item()
    cand={
        "player_name":"Connor McDavid",
        "player_match_confidence":"high",
        "set_name":"Upper Deck",
        "season":"2015-16",
        "card_identity_confidence_score":70,
    }
    out=classify_candidate_against_target(target,cand)
    assert out["status"]=="POSSIBLE_MATCH"
    assert out["exact_match"] is False

def test_optional_parallel_must_match_when_target_has_it():
    target=base_item(); target["parallel"]="Silver"
    cand=base_item(); cand["parallel"]="Gold"
    out=classify_candidate_against_target(target,cand)
    assert out["status"]=="WRONG_CARD"
    assert "parallel" in out["mismatch_fields"]

def test_report_only_uses_exact_supply_search_candidates_and_matching_query():
    target=base_item()
    target["search_expansion_query"]="Connor McDavid Upper Deck 2015-16 201"
    good=base_item()
    good.update({
        "tradera_item_id":"1",
        "search_expansion_kind":"exact-card-supply-query",
        "search_expansion_query":target["search_expansion_query"],
    })
    other=base_item()
    other.update({
        "tradera_item_id":"2",
        "search_expansion_kind":"player-exact",
        "search_expansion_query":"Connor McDavid",
    })
    report=build_confirmation_report(target,[good,other])
    assert report["confirmed_exact"]==1
    assert len(report["rows"])==1
    assert report["creates_value"] is False
