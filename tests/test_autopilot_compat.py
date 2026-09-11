from src.autopilot_compat import build_autopilot_plan_compat

def test_new_signature_gets_results():
    seen={}
    def planner(a,b,c,d,analyzed_results=None):
        seen["results"]=analyzed_results
        return {"status":"NEW"}
    out=build_autopilot_plan_compat(planner,1,2,3,4,analyzed_results=[{"x":1}])
    assert out["status"]=="NEW"
    assert seen["results"]==[{"x":1}]

def test_legacy_signature_is_called_without_new_kwarg():
    def planner(a,b,c,d):
        return {"status":"LEGACY","args":[a,b,c,d]}
    out=build_autopilot_plan_compat(planner,1,2,3,4,analyzed_results=[{"x":1}])
    assert out["status"]=="LEGACY"
    assert out["args"]==[1,2,3,4]
