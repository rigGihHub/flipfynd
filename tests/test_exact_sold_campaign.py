from src.exact_sold_campaign import build_exact_sold_campaign


def exact_sold(player="A", set_name="Set", season="2025-26", card_number="10", source="Tradera"):
    return {
        "titel": f"{player} {set_name} #{card_number}",
        "sold_price": 100,
        "sold_verification_status": "verified",
        "sale_evidence_type": "explicit_sold_price",
        "player_name": player,
        "set_name": set_name,
        "season": season,
        "card_number": card_number,
        "identity_verified": True,
        "identity_evidence_source": "manual_review",
        "source_platform": source,
    }


def candidate(player="A", card_number="10", score=50):
    return {
        "titel": f"{player} card",
        "opportunity_priority_score": score,
        "exact_identity_gate_identity_fields": {
            "player_name": player,
            "set_name": "Set",
            "season": "2025-26",
            "card_number": card_number,
        },
    }


def test_campaign_counts_only_exact_ready_sales_toward_goal():
    good = exact_sold()
    bad = dict(good)
    bad["sold_verification_status"] = ""

    out = build_exact_sold_campaign([candidate(player="B")], [good, bad], target=50, batch_size=10)

    assert out["exact_ready_count"] == 1
    assert out["remaining_to_target"] == 49
    assert out["status"] == "RESEARCH_ACTIVE"


def test_campaign_is_breadth_first_before_second_slot_for_same_identity():
    rows = [candidate(player="A", score=90), candidate(player="B", score=80), candidate(player="C", score=70)]

    out = build_exact_sold_campaign(rows, [], target=100, batch_size=4, per_identity_target=2)

    assert [task["identity"]["player_name"] for task in out["tasks"][:3]] == ["A", "B", "C"]
    assert out["tasks"][3]["identity"]["player_name"] == "A"
    assert out["tasks"][3]["research_round"] == 2


def test_thin_identity_gets_only_one_missing_slot_when_target_is_two():
    rows = [candidate(player="A"), candidate(player="B")]
    sold = [exact_sold(player="A")]

    out = build_exact_sold_campaign(rows, sold, target=100, batch_size=10, per_identity_target=2)
    a_tasks = [task for task in out["tasks"] if task["identity"]["player_name"] == "A"]
    b_tasks = [task for task in out["tasks"] if task["identity"]["player_name"] == "B"]

    assert len(a_tasks) == 1
    assert len(b_tasks) == 2


def test_duplicate_candidates_for_same_identity_do_not_duplicate_research_slots():
    rows = [candidate(player="A", score=20), candidate(player="A", score=90)]

    out = build_exact_sold_campaign(rows, [], target=100, batch_size=10, per_identity_target=2)

    assert out["actionable_identity_count"] == 1
    assert len(out["tasks"]) == 2
    assert all(task["priority_score"] == 90 for task in out["tasks"])


def test_campaign_stops_when_global_target_is_reached():
    sold = [exact_sold(player=f"P{i}", card_number=str(i)) for i in range(5)]

    out = build_exact_sold_campaign([candidate(player="X")], sold, target=5, batch_size=10)

    assert out["status"] == "TARGET_REACHED"
    assert out["remaining_to_target"] == 0
    assert out["tasks"] == []


def test_identity_blocked_candidates_do_not_create_fake_research_tasks():
    blocked = [{"titel": "Unknown card", "opportunity_priority_score": 99}]

    out = build_exact_sold_campaign(blocked, [], target=50, batch_size=10)

    assert out["status"] == "IDENTITY_BLOCKED"
    assert out["tasks"] == []
    assert out["identity_blocked_count"] == 1
