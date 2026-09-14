from src.sold_acquisition_program import build_sold_acquisition_program


def exact_ready(player, number):
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
        "card_number": str(number),
        "identity_verified": True,
        "identity_evidence_source": "manual_review",
    }


def candidate(player, number, score=50):
    return {
        "titel": f"{player} listing",
        "opportunity_priority_score": score,
        "exact_identity_gate_identity_fields": {
            "player_name": player,
            "set_name": "Set",
            "season": "2025-26",
            "card_number": str(number),
        },
    }


def test_program_builds_to_floor_first():
    rows = [exact_ready("A", 1), exact_ready("B", 2)]
    out = build_sold_acquisition_program(
        [candidate("C", 3)], rows, target_floor=3, target_goal=5, batch_size=5
    )
    assert out["phase"] == "BUILD_TO_FLOOR"
    assert out["current_target"] == 3
    assert out["remaining_to_current_target"] == 1
    assert out["next_task_count"] == 1


def test_program_expands_to_goal_after_floor():
    rows = [exact_ready("A", 1), exact_ready("B", 2), exact_ready("C", 3)]
    out = build_sold_acquisition_program(
        [candidate("D", 4)], rows, target_floor=3, target_goal=5, batch_size=5
    )
    assert out["phase"] == "EXPAND_TO_GOAL"
    assert out["current_target"] == 5
    assert out["remaining_to_current_target"] == 2


def test_program_stops_tasks_at_goal():
    rows = [exact_ready(f"P{i}", i) for i in range(5)]
    out = build_sold_acquisition_program(
        [candidate("X", 99)], rows, target_floor=3, target_goal=5, batch_size=5
    )
    assert out["phase"] == "GOAL_COMPLETE"
    assert out["remaining_to_current_target"] == 0
    assert out["next_tasks"] == []
