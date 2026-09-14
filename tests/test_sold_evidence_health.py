from src.sold_evidence_health import build_sold_evidence_health


def exact_ready(player="A", number="1"):
    return {
        "titel": f"{player} card",
        "sold_price": 100,
        "market_state": "sold",
        "sold_verification_status": "verified",
        "sale_evidence_type": "explicit_sold_price",
        "source_platform": "test",
        "player_name": player,
        "set_name": "Set",
        "season": "2025-26",
        "card_number": number,
        "identity_verified": True,
        "identity_evidence_source": "manual_review",
    }


def test_empty_store_reports_no_safe_sales():
    out = build_sold_evidence_health([])
    assert out["status"] == "NO_SAFE_SALES"
    assert out["safe_sale_count"] == 0
    assert out["exact_ready_count"] == 0
    assert out["remaining_to_floor"] == 50


def test_only_exact_ready_sales_count_toward_target():
    sale_only = {
        "titel": "Unknown exact identity",
        "sold_price": 80,
        "market_state": "sold",
        "sold_verification_status": "verified",
        "sale_evidence_type": "explicit_sold_price",
        "source_platform": "test",
    }
    out = build_sold_evidence_health([exact_ready(), sale_only], target_floor=2, target_goal=4)
    assert out["safe_sale_count"] == 2
    assert out["exact_ready_count"] == 1
    assert out["remaining_to_floor"] == 1
    assert out["goal_progress_pct"] == 25.0


def test_contradictory_legacy_sale_is_blocked_and_counted():
    bad = exact_ready()
    bad["market_state"] = "unsold"
    out = build_sold_evidence_health([bad])
    assert out["safe_sale_count"] == 0
    assert out["blocked_quality_count"] == 1
    assert out["contradictory_status_count"] == 1
    assert out["exact_ready_count"] == 0


def test_floor_and_goal_status_are_explicit():
    rows = [exact_ready(player=f"P{i}", number=str(i)) for i in range(3)]
    floor = build_sold_evidence_health(rows, target_floor=3, target_goal=5)
    goal = build_sold_evidence_health(rows, target_floor=2, target_goal=3)
    assert floor["status"] == "FLOOR_REACHED"
    assert floor["remaining_to_floor"] == 0
    assert goal["status"] == "GOAL_REACHED"
    assert goal["remaining_to_goal"] == 0
