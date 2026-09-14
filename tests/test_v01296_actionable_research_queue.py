from src.unlock_research_queue import build_unlock_research_queue


def test_ui_queue_does_not_pad_results_with_searchable_base_cards():
    ordinary = [
        {
            "titel": f"1978 ordinary base card #{number}",
            "sold_comparable_count": 0,
            "exact_identity_gate_supports_comp_research": True,
            "deal_score": 90,
        }
        for number in range(1, 11)
    ]

    queue = build_unlock_research_queue(ordinary, limit=10, actionable_only=True)

    assert queue["rows"] == []
    assert queue["suppressed_count"] == 10
    assert queue["total"] == 10


def test_ui_queue_keeps_card_specific_merit_and_evidence_near_unlock():
    rows = [
        {
            "titel": "Numbered rookie /99",
            "sold_comparable_count": 0,
            "exact_identity_gate_supports_comp_research": True,
            "serial_denominator": 99,
            "is_rookie": True,
            "rookie_importance_matched": True,
        },
        {
            "titel": "Ordinary card with one exact sold",
            "sold_comparable_count": 1,
            "exact_identity_gate_supports_exact_comp_search": True,
        },
    ]

    queue = build_unlock_research_queue(rows, limit=10, actionable_only=True)

    assert {row["title"] for row in queue["rows"]} == {
        "Numbered rookie /99",
        "Ordinary card with one exact sold",
    }
    assert queue["suppressed_count"] == 0
