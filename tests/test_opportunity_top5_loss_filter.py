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
