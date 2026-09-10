from src.research_action_center import build_research_actions


def base_item():
    return {
        "player_name": "Connor McDavid",
        "player_match_confidence": "high",
        "set_name": "Upper Deck",
        "season": "2015-16",
        "card_number": "201",
        "card_identity_confidence_score": 90,
        "identity_evidence_sources": {"player_name": ["a", "b"]},
        "decision": "BEVAKA",
        "sold_comparable_count": 1,
        "valuation_display_safe": False,
        "valuation_confidence_score": 50,
    }


def test_one_missing_sold_becomes_clear_next_action():
    out=build_research_actions(base_item(),[],[])
    ids=[x["action_id"] for x in out["actions"]]
    assert "FIND_VERIFIED_SOLD" in ids
    sold=next(x for x in out["actions"] if x["action_id"]=="FIND_VERIFIED_SOLD")
    assert sold["label"]=="Hitta 1 verifierad SOLD till"
    assert out["creates_buy_decision"] is False
    assert out["creates_sold_evidence"] is False


def test_missing_card_number_prioritized_as_identity_work():
    row=base_item(); row["card_number"]=""
    out=build_research_actions(row,[],[])
    assert out["next_action"]["action_id"] in {"VERIFY_CARD_NUMBER","STRENGTHEN_IDENTITY"}
    assert out["creates_identity"] is False


def test_parallel_flag_without_parallel_requests_verification():
    row=base_item(); row["is_parallel"]=True; row["parallel"]=""
    out=build_research_actions(row,[],[])
    assert any(x["action_id"]=="VERIFY_PARALLEL" for x in out["actions"])


def test_supply_history_gap_generates_snapshot_action():
    out=build_research_actions(base_item(),[],[])
    assert any(x["action_id"]=="CHECK_EXACT_SUPPLY" for x in out["actions"])
