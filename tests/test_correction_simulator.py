from src.correction_simulator import simulate_correction, build_correction_simulation
def row(ep=100,ap=70,er=50,ar=30,ed=10,ad=20):
 return {"status":"sålt","sport":"Hockey","expected_net_profit_at_capture":ep,"actual_net_profit":ap,
 "expected_roi_pct_at_capture":er,"actual_roi_pct":ar,"flip_velocity_days_at_capture":ed,"days_to_sell":ad}
def cand(signals=[("profit","optimistic",30)]):
 return {"segment":"sport","label":"Hockey","signals":signals}
def test_needs_five_rows():
 assert not simulate_correction([row() for _ in range(4)],cand())["metrics"]["profit"]["eligible"]
def test_median_shift_reduces_profit_error():
 r=simulate_correction([row() for _ in range(5)],cand())
 assert r["metrics"]["profit"]["shift"]==-30
 assert r["metrics"]["profit"]["mae_after"]==0
def test_velocity_shift():
 r=simulate_correction([row() for _ in range(5)],cand([("velocity","too_fast",10)]))
 assert r["metrics"]["velocity"]["shift"]==10
def test_all_tested_metrics_must_improve():
 rows=[row() for _ in range(5)]
 r=simulate_correction(rows,cand([("profit","optimistic",30),("roi","optimistic",20)]))
 assert r["worth_reviewing"] is True
def test_no_auto_change():
 r=build_correction_simulation([row() for _ in range(5)],{"candidates":[cand()]})
 assert r["automatic_model_changes"] is False and r["results"][0]["automatic_change"] is False
def test_empty_candidates():
 assert build_correction_simulation([],{"candidates":[]})["tested_count"]==0
