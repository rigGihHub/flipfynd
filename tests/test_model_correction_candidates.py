from src.model_correction_candidates import build_model_correction_candidates
def seg(count=5,pe=-30,re=-12,de=8,enough=True):
 return {"segment":"sport","label":"Hockey","count":count,"enough":enough,
 "profit":{"count":count,"median_error":pe},"roi":{"count":count,"median_error":re},
 "days_to_sell":{"count":count,"median_error":de}}
def test_small_segment_ignored():
 assert build_model_correction_candidates({"reviewable":[seg(count=4)]})["count"]==0
def test_optimistic_profit_creates_down_review():
 r=build_model_correction_candidates({"reviewable":[seg()]})
 assert "justeras ned" in r["candidates"][0]["suggestion"]
def test_slow_actual_sale_creates_velocity_review():
 r=build_model_correction_candidates({"reviewable":[seg(pe=0,re=0,de=10)]})
 assert "säljtid bör höjas" in r["candidates"][0]["suggestion"]
def test_small_errors_create_no_candidate():
 assert build_model_correction_candidates({"reviewable":[seg(pe=-5,re=-3,de=2)]})["count"]==0
def test_strong_requires_ten_and_multiple_signals():
 r=build_model_correction_candidates({"reviewable":[seg(count=10)]})
 assert r["candidates"][0]["strength"]=="Stark kandidat"
def test_never_auto_changes():
 r=build_model_correction_candidates({"reviewable":[seg()]})
 assert r["automatic_model_changes"] is False and r["candidates"][0]["automatic_change"] is False


def test_candidate_has_no_cross_unit_severity():
 r=build_model_correction_candidates({"reviewable":[seg()]})
 c=r["candidates"][0]
 assert "severity" not in c
 assert c["metric_errors"]["profit_kr"]==30
 assert c["metric_errors"]["roi_percentage_points"]==12
 assert c["metric_errors"]["velocity_days"]==8

def test_candidate_order_does_not_compare_error_units():
 a=seg(count=10,pe=-26,re=0,de=0); a["label"]="A"
 b=seg(count=10,pe=0,re=0,de=100); b["label"]="B"
 r=build_model_correction_candidates({"reviewable":[a,b]})
 assert all("severity" not in x for x in r["candidates"])
