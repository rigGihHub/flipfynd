from src.buy_decision_summary import build_buy_decision_summary
def cand():
    return {"titel":"A","analysis_total_cost":200,"max_total_price":240,"net_profit_estimate":100,"floor_profit_estimate":-20,"flip_velocity_expected_days":12,"flip_velocity_evidence":"verified_sold_velocity","lank":"x"}
def queue():
    return {"picks":[{"rank":1,"title":"A"}]}
def test_ready():
    assert build_buy_decision_summary(queue(), [cand()])["status"]=="READY"
def test_fields():
    r=build_buy_decision_summary(queue(), [cand()])["rows"][0]
    assert r["buy_total"]==200 and r["max_total"]==240 and r["likely_profit"]==100 and r["downside_profit"]==-20 and r["expected_days"]==12
def test_missing_candidate_skipped():
    assert build_buy_decision_summary(queue(), [])["status"]=="INSUFFICIENT_DATA"
def test_missing_profit_skipped():
    x=cand(); x["net_profit_estimate"]=None
    assert build_buy_decision_summary(queue(), [x])["status"]=="INSUFFICIENT_DATA"
def test_input_not_mutated():
    q=queue(); c=[cand()]
    build_buy_decision_summary(q,c)
    assert q==queue() and c[0]["titel"]=="A"
def test_no_new_assumptions():
    assert "inga nya antaganden" in build_buy_decision_summary(queue(), [cand()])["note"]
