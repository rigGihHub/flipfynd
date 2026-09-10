from src.research_action_center import build_low_click_action_plan

def base():
    return {"player_name":"A","player_match_confidence":"high","decision":"BEVAKA"}

def test_identity_gaps_are_grouped_into_one_primary_workflow():
    out=build_low_click_action_plan(base(),[],[])
    assert out["primary"]["workflow_id"]=="IDENTITY_WORKFLOW"
    assert out["primary"]["label"]=="Fixa kortidentiteten"
    assert out["creates_buy_decision"] is False

def test_one_primary_action_even_with_multiple_gaps():
    out=build_low_click_action_plan(base(),[],[])
    assert isinstance(out["primary"],dict)
    assert out["remaining_count"] >= 0
    assert out["creates_value"] is False
