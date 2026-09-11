from src.market_coverage_autopilot import build_autopilot_plan

def cov(complete=False, pages=12, next_page=13, freshness="fresh", missing=None):
    return {
        "complete":complete,
        "loaded_page_count":pages,
        "next_page":next_page,
        "freshness":freshness,
        "missing_pages":missing or [],
    }

def hockey_result(**extra):
    row={"source_category":"Hockey - NHL","deal_score":20,"confidence":20}
    row.update(extra)
    return row

def football_result(**extra):
    row={"source_category":"Fotboll","deal_score":20,"confidence":20}
    row.update(extra)
    return row

def test_build_targets_sport_with_weaker_candidate_evidence():
    results=[
        hockey_result(
            beslut="KÖP",
            deal_score=80,
            ranking_confidence_score=80,
            sold_comparable_count=3,
            exact_identity_gate_supports_exact_comp_search=True,
            valuation_display_safe=True,
        ),
        hockey_result(deal_score=70),
        football_result(deal_score=10),
    ]
    p=build_autopilot_plan(cov(),cov(),{"due":False},{"due":False},results)
    assert p["status"]=="BUILD"
    assert p["category"]=="Fotboll"
    assert p["target_sport"]=="Fotboll"

def test_build_uses_coverage_when_no_analysis_exists():
    p=build_autopilot_plan(
        cov(pages=20,next_page=21),
        cov(pages=4,next_page=5),
        {"due":False},{"due":False},
        [],
    )
    assert p["category"]=="Fotboll"

def test_refresh_still_overrides_gap_targeting():
    p=build_autopilot_plan(
        cov(freshness="stale"),
        cov(pages=2),
        {"due":True},{"due":False},
        [],
    )
    assert p["status"]=="REFRESH"
    assert p["category"]=="__all__"
    assert p["mode"]=="incremental"

def test_planner_never_changes_decision_logic():
    p=build_autopilot_plan(cov(),cov(),{"due":False},{"due":False},[])
    assert p["creates_decision"] is False
