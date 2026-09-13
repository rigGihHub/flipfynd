from src.unlock_research_queue import build_unlock_research_queue


def test_exact_identity_alone_does_not_beat_stronger_research_candidate():
    low_value_star_insert = {
        "titel": "2024-25 Upper Deck Series 1 Gaming FOV Speckle Nathan MacKinnon",
        "exact_identity_gate_supports_exact_comp_search": True,
        "exact_identity_gate_status": "EXACT",
        "sold_comparable_count": 0,
        "deal_score": 55,
        "collector_worth_score": 42,
        "collector_worth_verdict": "SPELARDRIVET_STANDARDKORT",
        "is_parallel": True,
    }
    stronger_card = {
        "titel": "Promising numbered rookie /99",
        "exact_identity_gate_supports_comp_research": True,
        "exact_identity_gate_status": "SÖKBAR_TITEL",
        "sold_comparable_count": 0,
        "deal_score": 45,
        "is_rookie": True,
        "rookie_importance_matched": True,
        "rookie_importance_score": 85,
        "serial_denominator": 99,
        "valuable_structure_score": 75,
    }

    queue = build_unlock_research_queue([low_value_star_insert, stronger_card], limit=2)

    assert queue["rows"][0]["title"] == "Promising numbered rookie /99"
    assert queue["rows"][1]["status"] == "EXACT_READY_LOW_MERIT"
    assert queue["low_merit_exact_count"] == 1


def test_one_sale_away_still_has_highest_research_leverage():
    one_away = {
        "titel": "Exact card with one sold",
        "exact_identity_gate_supports_exact_comp_search": True,
        "sold_comparable_count": 1,
    }
    premium_without_sales = {
        "titel": "1/1 autograph without sold",
        "exact_identity_gate_supports_exact_comp_search": True,
        "sold_comparable_count": 0,
        "is_1of1": True,
        "is_auto": True,
    }

    queue = build_unlock_research_queue([premium_without_sales, one_away], limit=2)

    assert queue["rows"][0]["status"] == "ONE_SALE_AWAY"
