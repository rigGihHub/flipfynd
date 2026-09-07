from src.buy_queue_risk_reward import build_risk_reward
def base(): return {"analysis_total_cost":200,"floor_profit_estimate":-20,"net_profit_estimate":100,"expected_resale":350,"best_case_resale":420}
def test_ready(): assert build_risk_reward(base())["status"]=="READY"
def test_roi(): assert build_risk_reward(base())["likely_roi_pct"]==50.0
def test_downside(): assert build_risk_reward(base())["capital_downside_pct"]==10.0
def test_band(): assert build_risk_reward(base())["risk_band"]=="Låg kapitalrisk"
def test_missing():
 x=base(); x["analysis_total_cost"]=None; assert build_risk_reward(x)["status"]=="INSUFFICIENT_DATA"
def test_no_invented_profit(): assert build_risk_reward(base())["strong_profit"] is None
