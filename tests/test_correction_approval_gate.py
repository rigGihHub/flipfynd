from src.correction_approval_gate import review_correction_candidate, build_correction_approval_gate

def good():
 return {"segment":"sport","label":"Hockey","passes_holdout":True,"discovery_count":5,"holdout_count":5,
 "metrics":{"profit":{"eligible":True,"discovery_count":5,"holdout_count":5,"shift":-20,
 "mae_before":30,"mae_after":20,"improvement_pct":33.3,"passes":True}}}

def test_good_candidate_review_ready():
 r=review_correction_candidate(good())
 assert r["status"]=="REVIEW_READY" and r["ready_for_manual_review"]

def test_failed_holdout_blocked():
 x=good(); x["passes_holdout"]=False
 r=review_correction_candidate(x)
 assert r["status"]=="NOT_READY" and "Klarade inte holdout-testet" in r["blockers"]

def test_small_holdout_blocked():
 x=good(); x["holdout_count"]=4
 r=review_correction_candidate(x)
 assert "För få holdout-utfall" in r["blockers"]

def test_metric_failure_blocked():
 x=good(); x["metrics"]["profit"]["passes"]=False
 r=review_correction_candidate(x)
 assert "Alla mått förbättrades inte" in r["blockers"]

def test_never_enables_production():
 r=review_correction_candidate(good())
 assert r["automatic_change"] is False and r["production_enabled"] is False

def test_gate_summary():
 r=build_correction_approval_gate({"results":[good()]})
 assert r["review_ready_count"]==1 and r["production_changes"] is False
