from src.decision_tiers import build_decision_tiers

def item(decision="SKIP",sold=0,identity=False,value=None,cost=32,max_total=0):
 return {"titel":"1995-96 Pinnacle #101 Wayne Gretzky","deal_score":90,"ranking_confidence_score":90,"sold_comparable_count":sold,"exact_identity_gate_supports_exact_comp_search":identity,"exact_identity_gate_identity_fields":{"player_name":"Wayne Gretzky"},"beslut":decision,"valuation_display_safe":value is not None,"market_value_estimate":value,"analysis_total_cost":cost,"max_total_price":max_total}

def test_cheap_famous_card_cannot_enter_top3_without_verified_edge():
 r=build_decision_tiers([item()], require_verified_economic_edge=True); assert r["rows"]==[]

def test_verified_buy_below_max_can_enter():
 r=build_decision_tiers([item("KÖP",3,True,120,50,75)], require_verified_economic_edge=True); assert len(r["rows"])==1

def test_above_max_is_rejected():
 r=build_decision_tiers([item("KÖP",5,True,25,32,18)], require_verified_economic_edge=True); assert r["rows"]==[]; assert any("överstiger" in k for k in r["rejection_reasons"])
