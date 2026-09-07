from src.best_buy_decision_card import build_best_buy_decision_card
def item(title="A",decision="KÖP",score=70,profit=100,cost=200,p30=80):
 return {"titel":title,"decision":decision,"analysis_total_cost":cost,"net_profit_estimate":profit,
 "floor_profit_estimate":-20,"expected_resale":350,"flip_velocity_expected_days":12,
 "max_total_price":240,"max_item_price":211,"max_price_shipping_assumption":29,
 "sale_probability":70,"exact_identity_gate_supports_dynamic_max_bid":True,"exact_identity_gate_status":"VERIFIERAD","flip_velocity_evidence":"verified_sold_velocity","capital_efficiency":{"score":score,"profit_30d":p30,"label":"Effektiv"}}
def test_no_candidate():
 assert build_best_buy_decision_card([])["status"]=="NO_SAFE_BUY"
def test_non_buy_never_selected():
 assert build_best_buy_decision_card([item(decision="AVSTÅ")])["status"]=="NO_SAFE_BUY"
def test_unscored_never_selected():
 assert build_best_buy_decision_card([item(score=None)])["status"]=="NO_SAFE_BUY"
def test_highest_capital_score_wins():
 r=build_best_buy_decision_card([item("A",score=60),item("B",score=80)])
 assert r["card"]["title"]=="B"
def test_profit30_breaks_tie():
 r=build_best_buy_decision_card([item("A",p30=50),item("B",p30=90)])
 assert r["card"]["title"]=="B"
def test_card_contains_action_fields():
 c=build_best_buy_decision_card([item()])["card"]
 assert c["total_cost"]==200 and c["net_profit"]==100 and c["max_total_price"]==240 and c["expected_days"]==12
