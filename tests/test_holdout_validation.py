from src.holdout_validation import validate_candidate_holdout, build_holdout_validation
def row(i,ep=100,ap=70,er=50,ar=30,ed=10,ad=20,ts=True):
 d={"id":str(i),"status":"sålt","sport":"Hockey","expected_net_profit_at_capture":ep,"actual_net_profit":ap,
 "expected_roi_pct_at_capture":er,"actual_roi_pct":ar,"flip_velocity_days_at_capture":ed,"days_to_sell":ad}
 if ts: d["prediction_timestamp_at_capture"]=f"2026-01-{i+1:02d}T10:00:00+00:00"
 return d
def cand(signals=[("profit","optimistic",30)]):
 return {"segment":"sport","label":"Hockey","signals":signals}
def test_requires_ten_segment_rows_total():
 r=validate_candidate_holdout([row(i) for i in range(9)],cand())
 assert r["temporal_status"]=="INSUFFICIENT_DATA" and r["discovery_count"]==0 and r["holdout_count"]==0
def test_discovery_shift_tested_on_later_predictions():
 r=validate_candidate_holdout([row(i) for i in range(10)],cand())
 assert r["temporal_status"]=="READY"
 assert r["metrics"]["profit"]["shift"]==-30
 assert r["metrics"]["profit"]["mae_after"]==0
 assert r["passes_holdout"] is True
def test_bad_later_holdout_fails():
 rows=[row(i) for i in range(5)] + [row(i+5,ap=130) for i in range(5)]
 r=validate_candidate_holdout(rows,cand())
 assert r["passes_holdout"] is False
def test_multiple_metrics_all_must_pass():
 r=validate_candidate_holdout([row(i) for i in range(10)],cand([("profit","optimistic",30),("roi","optimistic",20)]))
 assert r["passes_holdout"] is True
def test_missing_prediction_timestamp_abstains():
 rows=[row(i) for i in range(10)]
 rows[7].pop("prediction_timestamp_at_capture")
 r=validate_candidate_holdout(rows,cand())
 assert r["temporal_status"]=="MISSING_DATES"
 assert r["missing_prediction_timestamp_count"]==1
 assert r["passes_holdout"] is False
def test_sale_date_or_id_never_used_as_fallback():
 rows=[row(i,ts=False) for i in range(10)]
 for i,x in enumerate(rows):
  x["sale_date"]=f"2026-02-{i+1:02d}"
  x["updated_at"]=f"2026-01-{i+1:02d}T10:00:00+00:00"
 r=validate_candidate_holdout(rows,cand())
 assert r["temporal_status"]=="MISSING_DATES"
 assert r["passes_holdout"] is False
def test_sort_is_by_prediction_time_not_input_order():
 rows=[row(i) for i in range(10)]
 rows=list(reversed(rows))
 r=validate_candidate_holdout(rows,cand())
 assert r["temporal_status"]=="READY"
 assert r["passes_holdout"] is True
def test_no_auto_changes():
 r=build_holdout_validation([row(i) for i in range(10)],{"candidates":[cand()]})
 assert r["automatic_model_changes"] is False and r["results"][0]["automatic_change"] is False
def test_empty():
 assert build_holdout_validation([],{"candidates":[]})["tested_count"]==0
