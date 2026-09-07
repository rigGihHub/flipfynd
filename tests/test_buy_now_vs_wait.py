from src.buy_now_vs_wait import build_buy_timing
def base(total=180,max_total=200,decision="KÖP"):
 return {"decision":decision,"analysis_total_cost":total,"max_total_price":max_total,"risk_score":99,"decision_confidence_audit_score":1}
def test_within_max(): assert build_buy_timing(base(170,200))["action"]=="INOM MAXPRIS"
def test_at_max_is_within(): assert build_buy_timing(base(200,200))["action"]=="INOM MAXPRIS"
def test_over_max(): assert build_buy_timing(base(210,200))["action"]=="ÖVER MAXPRIS"
def test_non_buy(): assert build_buy_timing(base(decision="AVSTÅ"))["action"]=="BEVAKA"
def test_missing_max():
 x=base(); x["max_total_price"]=None
 assert build_buy_timing(x)["status"]=="INSUFFICIENT_DATA"
def test_risk_and_confidence_do_not_create_new_timing_thresholds():
 assert build_buy_timing(base(170,200))["action"]=="INOM MAXPRIS"
