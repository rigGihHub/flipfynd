from src.best_buy_decision_card import build_best_buy_decision_card
from src.top_buy_queue import build_top_buy_queue
from src.buy_decision_summary import build_buy_decision_summary

def item(title="A", verified_identity=True, velocity_evidence="verified_sold_velocity", days=12, score=70, p30=80, profit=100):
    return {"titel":title,"decision":"KÖP","analysis_total_cost":200,"net_profit_estimate":profit,"floor_profit_estimate":-20,"expected_resale":350,"flip_velocity_expected_days":days,"flip_velocity_evidence":velocity_evidence,"max_total_price":240,"exact_identity_gate_supports_dynamic_max_bid":verified_identity,"exact_identity_gate_status":"VERIFIERAD" if verified_identity else "GRANSKA","capital_efficiency":{"score":score,"profit_30d":p30,"label":"Effektiv"},"lank":"https://example.test/"+title}

def test_best_buy_blocks_unverified_identity(): assert build_best_buy_decision_card([item(verified_identity=False)])["status"]=="NO_SAFE_BUY"
def test_queue_blocks_unverified_identity(): assert build_top_buy_queue([item(verified_identity=False)])["status"]=="NO_SAFE_BUYS"
def test_best_buy_hides_unverified_velocity():
    r=build_best_buy_decision_card([item(velocity_evidence="heuristic")]); assert r["card"]["expected_days"] is None and r["card"]["velocity_verified"] is False
def test_queue_hides_unverified_velocity(): assert build_top_buy_queue([item(velocity_evidence="heuristic")])["picks"][0]["expected_days"] is None
def test_queue_does_not_compare_unverified_velocity():
    a=item("A",velocity_evidence="heuristic",days=5,score=80); b=item("B",velocity_evidence="heuristic",days=20,score=70); assert not any("försäljning" in x for x in build_top_buy_queue([a,b])["picks"][0]["why_ahead"])
def test_summary_hides_unverified_velocity():
    x=item(velocity_evidence="heuristic"); q=build_top_buy_queue([x]); assert build_buy_decision_summary(q,[x])["rows"][0]["expected_days"] is None
def test_deterministic_tie_break_title(): assert build_top_buy_queue([item("B"),item("A")])["picks"][0]["title"]=="A"
def test_best_buy_deterministic_tie_break_title(): assert build_best_buy_decision_card([item("B"),item("A")])["card"]["title"]=="A"
