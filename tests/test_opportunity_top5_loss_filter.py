from src.opportunity_top5 import build_opportunity_top5
from src.seller_profit_display import known_negative_net_profit


def test_known_fee_adjusted_losses_cannot_consume_top_five_slots():
    listings = []
    for index in range(6):
        listings.append({
            "titel": f"2024 Topps Chrome Player {index} #12",
            "lank": f"https://www.tradera.com/item/{index}",
            "analysis_total_cost": 100,
            "asking_price_opportunity": {
                "status": "POSSIBLE_FIND",
                "possible_find": True,
                "reference_asking_price": 200 if index < 5 else 160,
                "net_margin": -20 if index < 5 else 25,
                "comparison_count": 3,
                "comparisons": [],
            },
        })

    selected = build_opportunity_top5(listings, limit=5)["rows"]
    assert [row["url"] for row in selected] == ["https://www.tradera.com/item/5"]
    assert all(not known_negative_net_profit(row) for row in selected)


def test_negative_model_indications_do_not_fill_an_unsafe_top_five():
    listings = [{
        "titel": f"2024 Topps Chrome Player {index} #12",
        "lank": f"https://www.tradera.com/item/model-{index}",
        "analysis_total_cost": 60,
        "guide_price": 20 + index,
    } for index in range(5)]
    assert build_opportunity_top5(listings, limit=5)["rows"] == []


def test_low_model_guide_does_not_hide_positive_exact_active_comparison():
    listing = {
        "titel": "2023-24 Upper Deck Young Guns #201 Player Example",
        "lank": "https://www.tradera.com/item/active-comp",
        "analysis_total_cost": 35,
        "guide_price": 10,
        "asking_price_opportunity": {
            "status": "POSSIBLE_FIND", "possible_find": True,
            "reference_asking_price": 90, "net_margin": 43,
            "comparison_count": 2, "comparisons": [],
        },
    }
    result = build_opportunity_top5([listing], limit=5)["rows"]
    assert len(result) == 1
    assert result[0]["asking_positive"] is True
    assert result[0]["practical_price_source"] == "ACTIVE_PRICE"
    assert result[0]["practical_margin"] == 55
