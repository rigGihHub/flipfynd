from src.evidence_scenario_range import build_evidence_scenario_range

def r(p,i): return {"price":p,"sold_comp_id":i}

def test_blocked_without_decision_grade():
 x=build_evidence_scenario_range([r(100,"1"),r(120,"2"),r(140,"3")],decision_grade=False)
 assert x["status"]=="BLOCKED" and not x["available"]

def test_observed_low_median_high():
 x=build_evidence_scenario_range([r(100,"1"),r(120,"2"),r(140,"3")],decision_grade=True)
 assert [s["resale_price"] for s in x["scenarios"]]==[100,120,140]

def test_even_median_is_statistical_median():
 x=build_evidence_scenario_range([r(100,"1"),r(120,"2"),r(140,"3"),r(160,"4")],decision_grade=True)
 assert x["price_median"]==130

def test_duplicates_collapsed_before_range():
 rows=[r(100,"1"),r(100,"1"),r(120,"2"),r(140,"3")]
 x=build_evidence_scenario_range(rows,decision_grade=True)
 assert x["independent_count"]==3
 assert x["all_observed_prices"]==[100,120,140]

def test_net_profit_uses_same_fee_shape_and_packaging():
 x=build_evidence_scenario_range([r(200,"1"),r(220,"2"),r(240,"3")],total_cost=100,decision_grade=True)
 likely=x["scenarios"][1]
 assert likely["selling_fee"]==22
 assert likely["packaging"]==3
 assert likely["net_profit"]==95
 assert likely["roi_pct"]==95.0

def test_missing_cost_keeps_price_scenarios_without_fake_profit():
 x=build_evidence_scenario_range([r(100,"1"),r(120,"2"),r(140,"3")],decision_grade=True)
 assert x["scenarios"][1]["net_profit"] is None
 assert x["scenarios"][1]["roi_pct"] is None

def test_no_percentile_or_probability_fields():
 x=build_evidence_scenario_range([r(100,"1"),r(120,"2"),r(140,"3")],decision_grade=True)
 assert "probability" not in x
 assert all("probability" not in s for s in x["scenarios"])
