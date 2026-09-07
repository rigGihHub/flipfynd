from src.top_buy_decision_compare import build_top_buy_decision_compare

def item(title,total=200,weak=-20,likely=100,liq=75,evidence="sold",days=15):
 return {"titel":title,"analysis_total_cost":total,"floor_profit_estimate":weak,"net_profit_estimate":likely,
 "liquidity_score":liq,"liquidity_label":"Lättsålt","liquidity_evidence":evidence,
 "flip_velocity_expected_days":days,"flip_velocity_evidence":"verified_sold_velocity",
 "capital_efficiency":{"score":80,"profit_30d":120},"lank":"https://example.com"}

def queue():
 return {"picks":[{"rank":1,"title":"A"},{"rank":2,"title":"B"}]}

def test_ready():
 assert build_top_buy_decision_compare(queue(),[item("A"),item("B")])["status"]=="READY"

def test_preserves_queue_order():
 r=build_top_buy_decision_compare(queue(),[item("B"),item("A")])
 assert [x["title"] for x in r["rows"]]==["A","B"]
 assert r["ranking_changed"] is False

def test_profit_and_roi():
 r=build_top_buy_decision_compare(queue(),[item("A",total=200,weak=-20,likely=100),item("B")])["rows"][0]
 assert r["weak_roi_pct"]==-10.0 and r["likely_roi_pct"]==50.0

def test_verified_sell_days_only():
 x=item("A"); x["flip_velocity_evidence"]="heuristic"
 r=build_top_buy_decision_compare({"picks":[{"rank":1,"title":"A"}]},[x])["rows"][0]
 assert r["verified_sell_days"] is None

def test_missing_weak_does_not_invent_downside():
 x=item("A",weak=None)
 r=build_top_buy_decision_compare({"picks":[{"rank":1,"title":"A"}]},[x])["rows"][0]
 assert r["weak_profit"] is None and r["weak_roi_pct"] is None

def test_sellability_is_exposed_not_reweighted():
 r=build_top_buy_decision_compare({"picks":[{"rank":1,"title":"A"}]},[item("A",liq=62)])["rows"][0]
 assert r["sellability_score"]==62


def test_turnover_uses_verified_velocity():
 r=build_top_buy_decision_compare({"picks":[{"rank":1,"title":"A"}]},[item("A",total=200,likely=100,days=15)])["rows"][0]
 assert r["turnover"]["verified"] is True
 assert r["turnover"]["cycles_30d"]==2.0
 assert r["turnover"]["profit_30d"]==200.0
 assert r["turnover"]["roi_30d_pct"]==100.0

def test_turnover_abstains_without_verified_velocity():
 x=item("A",days=15); x["flip_velocity_evidence"]="heuristic"
 r=build_top_buy_decision_compare({"picks":[{"rank":1,"title":"A"}]},[x])["rows"][0]
 assert r["turnover"] is None

def test_profit_per_capital_day_is_dimensionally_explicit():
 r=build_top_buy_decision_compare({"picks":[{"rank":1,"title":"A"}]},[item("A",total=200,likely=100,days=20)])["rows"][0]
 assert r["turnover"]["profit_per_1000_capital_days"]==25.0
