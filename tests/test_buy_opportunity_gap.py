from src.buy_opportunity_gap import build_opportunity_gap
def test_ready(): assert build_opportunity_gap({"analysis_total_cost":215},{"action":"ÖVER MAXPRIS"},{"target_total":200})["status"]=="READY"
def test_gap(): assert build_opportunity_gap({"analysis_total_cost":215},{"action":"ÖVER MAXPRIS"},{"target_total":200})["gap_kr"]==15
def test_pct(): assert build_opportunity_gap({"analysis_total_cost":220},{"action":"ÖVER MAXPRIS"},{"target_total":200})["gap_pct"]==9.1
def test_no_arbitrary_band(): assert "band" not in build_opportunity_gap({"analysis_total_cost":215},{"action":"ÖVER MAXPRIS"},{"target_total":200})
def test_not_applicable(): assert build_opportunity_gap({"analysis_total_cost":195},{"action":"INOM MAXPRIS"},{"target_total":200})["status"]=="NOT_APPLICABLE"
def test_missing(): assert build_opportunity_gap({"analysis_total_cost":215},{"action":"ÖVER MAXPRIS"},{})["status"]=="INSUFFICIENT_DATA"
