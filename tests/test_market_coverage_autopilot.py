from src.market_coverage_autopilot import build_autopilot_plan, autopilot_progress_text

def cov(complete=False, pages=12, next_page=13, freshness="fresh"):
    return {"complete":complete,"loaded_page_count":pages,"next_page":next_page,"freshness":freshness}

def test_builds_one_prioritised_market_when_fresh_but_incomplete():
    p=build_autopilot_plan(cov(),cov(),{"due":False},{"due":False})
    assert p["status"]=="BUILD"
    assert p["category"] in {"Hockey - NHL","Fotboll"}
    assert p["mode"]=="market_batch"
    assert "Prioritet:" in autopilot_progress_text(p)

def test_refresh_has_priority_over_deeper_coverage():
    p=build_autopilot_plan(cov(freshness="stale"),cov(),{"due":True},{"due":False})
    assert p["status"]=="REFRESH"
    assert p["mode"]=="incremental"
    assert p["category"]=="__all__"

def test_ready_when_complete_and_fresh():
    p=build_autopilot_plan(cov(True),cov(True),{"due":False},{"due":False})
    assert p["status"]=="READY"
    assert p["mode"] is None
    assert p["creates_decision"] is False
