from src.prediction_outcome_validation import build_prediction_outcome_validation
def r(ep=100,ap=80,er=50,ar=40,ed=10,ad=15,status="sålt"):
 return {"status":status,"expected_net_profit_at_capture":ep,"actual_net_profit":ap,"expected_roi_pct_at_capture":er,"actual_roi_pct":ar,"flip_velocity_days_at_capture":ed,"days_to_sell":ad}
def test_open_ignored(): assert build_prediction_outcome_validation([r(status="köpt")])["sold_count"]==0
def test_profit_overestimated(): assert build_prediction_outcome_validation([r()])["profit"]["bias"]=="overestimated"
def test_velocity_longer(): assert build_prediction_outcome_validation([r()])["days_to_sell"]["median_error"]==5
def test_missing_not_reconstructed():
 x=r(); x["expected_net_profit_at_capture"]=None
 assert build_prediction_outcome_validation([x])["profit"]["count"]==0
def test_five_enough(): assert build_prediction_outcome_validation([r() for _ in range(5)])["profit"]["enough"]
def test_twenty_review_ready(): assert build_prediction_outcome_validation([r() for _ in range(20)])["review_ready"]
