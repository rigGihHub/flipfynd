from src.novice_navigation import (
    build_ending_soon_view,
    build_research_view,
    build_watch_view,
)


def test_ending_soon_view_only_surfaces_existing_eligible_auction():
    rows = [
        {
            "titel": "Card A",
            "sale_type": "Auktion",
            "exact_end_text": "2 timmar 10 minuter",
            "total_cost": 100,
            "max_total_price": 150,
            "valuation_confidence_score": 80,
            "exact_identity_gate_score": 90,
            "risk_score": 20,
            "sold_comparable_count": 3,
            "exact_identity_gate_supports_dynamic_max_bid": True,
            "detail_evidence_fusion_has_conflict": False,
            "is_lot": False,
            "beslut": "KANSKE",
        },
        {"titel": "Card B", "sale_type": "Köp nu"},
    ]
    view = build_ending_soon_view(rows)
    assert view["status"] == "READY"
    assert [row["title"] for row in view["rows"]] == ["Card A"]
    assert view["rows"][0]["decision"] == "KANSKE"
    assert view["creates_new_decision"] is False


def test_watch_view_never_upgrades_existing_watch_state():
    view = build_watch_view([
        {
            "titel": "Watch card",
            "beslut": "KANSKE",
            "opportunity_action": "BEVAKA",
            "opportunity_priority_score": 88,
            "decision_diagnostics": ["saknar verifierade sold comps"],
        }
    ])
    assert view["status"] == "READY"
    assert view["rows"][0]["decision"] == "KANSKE"
    assert "saknar verifierade sold comps" in view["rows"][0]["primary_blocker"]
    assert view["creates_new_decision"] is False


def test_research_view_keeps_research_as_research():
    view = build_research_view([
        {
            "titel": "Interesting rookie",
            "beslut": "SKIP",
            "mispriced_rookie_candidate": True,
            "is_information_edge_candidate": True,
            "information_edge_verify_first": ["card number", "parallel"],
        }
    ])
    assert view["status"] == "READY"
    assert view["rows"][0]["decision"] == "SKIP"
    assert len(view["rows"][0]["signals"]) == 2
    assert view["creates_new_decision"] is False


def test_empty_views_fail_closed():
    assert build_ending_soon_view([])["status"] == "EMPTY"
    assert build_watch_view([])["status"] == "EMPTY"
    assert build_research_view([])["status"] == "EMPTY"

from src.novice_navigation import build_best_available_view


def test_best_available_returns_top_three_without_upgrading_decisions():
    rows = [
        {"titel": "Weak A", "beslut": "SKIP", "opportunity_priority_score": 80, "deal_score": 20},
        {"titel": "Watch B", "beslut": "BEVAKA", "opportunity_priority_score": 90, "deal_score": 30},
        {"titel": "Weak C", "beslut": "SKIP", "opportunity_priority_score": 70, "deal_score": 50},
        {"titel": "Weak D", "beslut": "SKIP", "opportunity_priority_score": 60, "deal_score": 99},
    ]
    view = build_best_available_view(rows, limit=3)
    assert view["status"] == "READY"
    assert [r["title"] for r in view["rows"]] == ["Watch B", "Weak A", "Weak C"]
    assert [r["decision"] for r in view["rows"]] == ["BEVAKA", "SKIP", "SKIP"]
    assert view["creates_new_decision"] is False


def test_best_available_can_surface_skips_hidden_by_normal_display_filters():
    view = build_best_available_view([
        {"titel": "Only analysed card", "beslut": "SKIP", "deal_score": 11, "confidence": 12}
    ])
    assert view["status"] == "READY"
    assert view["rows"][0]["decision"] == "SKIP"


def test_best_available_empty_is_explicit():
    assert build_best_available_view([])["status"] == "EMPTY"
