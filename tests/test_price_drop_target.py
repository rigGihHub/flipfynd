from src.price_drop_target import build_price_drop_target
def base():
 return {"analysis_total_cost":215,"max_total_price":200,"max_price_shipping_assumption":29}
def test_over_max_target_ready(): assert build_price_drop_target(base(),{"action":"ÖVER MAXPRIS"})["status"]=="READY"
def test_target_equals_existing_max(): assert build_price_drop_target(base(),{"action":"ÖVER MAXPRIS"})["target_total"]==200
def test_item_target_subtracts_shipping(): assert build_price_drop_target(base(),{"action":"ÖVER MAXPRIS"})["target_item_price"]==171
def test_drop_needed(): assert build_price_drop_target(base(),{"action":"ÖVER MAXPRIS"})["drop_needed"]==15
def test_not_applicable_within_max(): assert build_price_drop_target(base(),{"action":"INOM MAXPRIS"})["status"]=="NOT_APPLICABLE"
def test_missing_max_abstains():
 x=base(); x["max_total_price"]=None
 assert build_price_drop_target(x,{"action":"ÖVER MAXPRIS"})["status"]=="INSUFFICIENT_DATA"
