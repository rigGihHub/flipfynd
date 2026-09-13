from src.research_candidate_matcher import match_research_candidate, rank_research_candidates
from src.auto_comp_research import research_one


def ident():
    return {"player_name":"Wayne Gretzky","season":"1995-96","set_name":"Pinnacle","card_number":"101"}


def test_strong_candidate_for_same_base_card():
    out=match_research_candidate(ident(), {"title":"1995-96 Pinnacle #101 Wayne Gretzky", "source":"eBay"})
    assert out["label"] in {"STRONG_CANDIDATE", "REVIEW"}
    assert "spelare" in out["matches"]
    assert "kortnummer" in out["matches"]
    assert out["creates_sold_evidence"] is False


def test_parallel_variant_is_rejected_for_base_target():
    out=match_research_candidate(ident(), {"title":"1995-96 Pinnacle #101 Wayne Gretzky Rink Collection"})
    assert out["label"] == "REJECT"
    assert "extra parallel" in out["conflicts"]


def test_wrong_card_number_is_rejected():
    out=match_research_candidate(ident(), {"title":"1995-96 Pinnacle #102 Wayne Gretzky"})
    assert out["label"] == "REJECT"
    assert "kortnummer" in out["conflicts"]


def test_ranker_puts_good_match_before_reject():
    rows=rank_research_candidates(ident(), [
        {"title":"1995-96 Pinnacle #102 Wayne Gretzky"},
        {"title":"1995-96 Pinnacle #101 Wayne Gretzky"},
    ])
    assert rows[0]["label"] != "REJECT"
    assert rows[-1]["label"] == "REJECT"


def test_auto_research_exposes_candidate_matches_without_promoting_them():
    item={
        "titel":"1995-96 Pinnacle #101 Wayne Gretzky",
        "exact_identity_gate_supports_comp_research":True,
        "exact_identity_gate_research_identity_fields":ident(),
    }
    sold=[{"title":"1995-96 Pinnacle #101 Wayne Gretzky","source":"eBay","sold_at":"2026-08-01"}]
    out=research_one(item, sold_records=sold)
    assert out["candidate_matches"]
    assert out["creates_sold_evidence"] is False
    assert out["creates_buy_decision"] is False
