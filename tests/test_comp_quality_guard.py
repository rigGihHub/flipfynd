from datetime import datetime, timezone
from src.comp_quality_guard import build_comp_quality_guard

NOW=datetime(2026,9,6,tzinfo=timezone.utc)

def row(price, date="2026-08-15"):
    return {"price":price,"sold_at":date}

def test_ready_with_three_recent_stable_exact_comps():
    r=build_comp_quality_guard([row(100),row(110),row(120)],now=NOW)
    assert r["status"]=="READY"
    assert r["decision_grade"] is True

def test_two_exact_comps_are_too_thin():
    r=build_comp_quality_guard([row(100),row(110)],now=NOW)
    assert r["status"]=="THIN"
    assert r["decision_grade"] is False

def test_wide_spread_blocks_decision_grade():
    r=build_comp_quality_guard([row(50),row(100),row(200)],now=NOW)
    assert r["status"]=="DISPERSED"

def test_old_exact_comps_are_stale():
    r=build_comp_quality_guard([row(100,"2025-01-01"),row(105,"2025-02-01"),row(110,"2025-03-01")],now=NOW)
    assert r["status"]=="STALE"
    assert r["recent_count"]==0

def test_missing_dates_fail_closed():
    r=build_comp_quality_guard([{"price":100},{"price":105},{"price":110}],now=NOW)
    assert r["status"]=="MISSING_DATES"

def test_missing_one_date_is_warning_not_block_when_rest_is_recent():
    r=build_comp_quality_guard([row(100),row(105),{"price":110}],now=NOW)
    assert r["status"]=="READY"
    assert r["warnings"]

def test_future_date_blocks():
    r=build_comp_quality_guard([row(100),row(105),row(110,"2026-10-01")],now=NOW)
    assert r["decision_grade"] is False

def test_no_rows_is_not_ready():
    r=build_comp_quality_guard([],now=NOW)
    assert r["status"]=="NO_EXACT_COMPS"


def test_source_diversity_is_metadata_not_new_decision_threshold():
    rows=[
        {"price":100,"sold_at":"2026-08-01","sold_comp_id":"1","source_platform":"eBay","saljare":"A"},
        {"price":105,"sold_at":"2026-08-02","sold_comp_id":"2","source_platform":"eBay","saljare":"B"},
        {"price":110,"sold_at":"2026-08-03","sold_comp_id":"3","source_platform":"eBay","saljare":"C"},
    ]
    r=build_comp_quality_guard(rows,now=NOW)
    assert r["source_diversity"]["status"]=="CONCENTRATED"
    assert r["decision_grade"] is True


def test_recency_transparency_metadata_only():
 r=build_comp_quality_guard([row(100,"2026-08-01"),row(105,"2026-08-02"),row(110,"2026-08-03")],now=NOW)
 assert r["decision_grade"] is True and r["recency_transparency"]["status"]=="DESCRIBED"

def test_market_direction_is_metadata_only_not_new_quality_rule():
    rows=[row(120,"2026-08-01"),row(110,"2026-08-02"),row(100,"2026-08-03")]
    r=build_comp_quality_guard(rows,now=NOW)
    assert r["decision_grade"] is True
    assert r["market_direction"]["direction"]=="DOWN"


def test_market_direction_evidence_is_descriptive_only():
 r=build_comp_quality_guard([row(100,"2026-08-01"),row(105,"2026-08-02"),row(110,"2026-08-03")],now=NOW)
 assert r["decision_grade"] is True
 assert r["market_direction_evidence"]["status"]=="DESCRIBED"
 assert "score" not in r["market_direction_evidence"]
