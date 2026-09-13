from src.decision_tiers import build_decision_tiers
from src.decision_tiers_compat import build_decision_tiers_compat


def test_ordinary_low_potential_exact_id_is_not_called_best_alternative():
    ordinary = {
        "titel": "2024-25 Upper Deck Gaming FOV Speckle Nathan MacKinnon",
        "beslut": "SKIP",
        "deal_score": 18,
        "ranking_confidence_score": 80,
        "sold_comparable_count": 0,
        "exact_identity_gate_supports_exact_comp_search": True,
        "exact_identity_gate_supports_comp_research": True,
        "collector_worth_score": 50,
        "card_hierarchy_score": 20,
    }
    stronger = {
        "titel": "Numbered rookie target /99",
        "beslut": "SKIP",
        "deal_score": 62,
        "ranking_confidence_score": 65,
        "sold_comparable_count": 0,
        "exact_identity_gate_supports_comp_research": True,
        "collector_worth_score": 78,
        "card_hierarchy_score": 82,
        "features": {"is_rookie": True, "is_serial_numbered": True},
    }

    result = build_decision_tiers_compat(
        build_decision_tiers,
        [ordinary, stronger],
        total_limit=3,
        require_verified_economic_edge=True,
    )

    titles = [row["title"] for row in result["rows"]]
    assert "Numbered rookie target /99" in titles
    assert "2024-25 Upper Deck Gaming FOV Speckle Nathan MacKinnon" not in titles
    assert result["suppressed_weak_ordinary_count"] == 1


def test_special_signal_survives_quality_gate_even_with_low_potential():
    oddity = {
        "titel": "Low-score but misclassified oddity",
        "beslut": "SKIP",
        "deal_score": 18,
        "ranking_confidence_score": 60,
        "sold_comparable_count": 0,
        "exact_identity_gate_supports_comp_research": True,
        "collector_worth_score": 35,
        "card_hierarchy_score": 20,
        "is_information_edge_candidate": True,
    }
    result = build_decision_tiers_compat(
        build_decision_tiers,
        [oddity],
        total_limit=3,
        require_verified_economic_edge=True,
    )
    assert [row["title"] for row in result["rows"]] == ["Low-score but misclassified oddity"]
