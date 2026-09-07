from src.watch_priority import build_watch_priority, build_watch_priority_queue
def item(): return {"analysis_total_cost":220,"net_profit_estimate":100,"capital_efficiency_score":99}
def test_ready(): assert build_watch_priority(item(),{"action":"ÖVER MAXPRIS"},{"gap_kr":20,"gap_pct":9.1})["status"]=="READY"
def test_no_synthetic_score(): assert "score" not in build_watch_priority(item(),{"action":"ÖVER MAXPRIS"},{"gap_kr":20,"gap_pct":9.1})
def test_not_applicable_within_max(): assert build_watch_priority(item(),{"action":"INOM MAXPRIS"},{"gap_kr":0})["status"]=="NOT_APPLICABLE"
def test_missing_gap_abstains(): assert build_watch_priority(item(),{"action":"ÖVER MAXPRIS"},{})["status"]=="INSUFFICIENT_DATA"
def test_label_is_descriptive(): assert build_watch_priority(item(),{"action":"ÖVER MAXPRIS"},{"gap_kr":20})["label"]=="Bevaka – närmast maxpris"
def test_does_not_change_input():
 x=item(); before=dict(x); build_watch_priority(x,{"action":"ÖVER MAXPRIS"},{"gap_kr":20}); assert x==before
def test_queue_orders_by_actual_gap_only():
 q={"picks":[{"rank":1,"title":"A"},{"rank":2,"title":"B"}]}
 c=[{"titel":"A"},{"titel":"B"}]
 tm=[{"rank":1,"timing":{"action":"ÖVER MAXPRIS"}},{"rank":2,"timing":{"action":"ÖVER MAXPRIS"}}]
 gp=[{"rank":1,"gap":{"gap_kr":30,"gap_pct":10}},{"rank":2,"gap":{"gap_kr":10,"gap_pct":5}}]
 r=build_watch_priority_queue(q,c,tm,gp)
 assert r["ready"][0]["title"]=="B"
