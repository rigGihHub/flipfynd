from src.seller_inventory_triage import build_seller_inventory_triage


def _fake_analyze(item, mode="fast", strategy_mode="quick_flip", sport="hockey"):
    title = item.get("titel", "")
    strong = "Young Guns" in title
    return {
        "decision": "UNDERSÖK",
        "exact_identity_gate_score": 90 if strong else 40,
        "exact_identity_gate_supports_exact_comp_search": bool(strong),
        "sold_comparable_count": 2 if strong else 0,
        "valuation_confidence_score": 80 if strong else 30,
        "rank_score": 75 if strong else 20,
        "market_edge_score": 70 if strong else 10,
    }


def test_triage_scans_all_matched_inventory_but_bounds_fast_analysis():
    items = []
    for idx in range(30):
        items.append({
            "tradera_item_id": str(idx),
            "titel": f"Base card {idx}",
            "pris": 10 + idx,
            "saljare": "Etanol71",
        })
    items.append({
        "tradera_item_id": "yg-1",
        "titel": "Upper Deck Young Guns Rookie",
        "pris": 50,
        "saljare": "Etanol71",
    })
    items.append({
        "tradera_item_id": "other",
        "titel": "Upper Deck Young Guns Other Seller",
        "pris": 1,
        "saljare": "Etanol710",
    })

    result = build_seller_inventory_triage(
        "etanol71",
        items,
        analyze_fn=_fake_analyze,
        max_fast_analyses=10,
        top_n=20,
    )

    assert result["inventory_count"] == 31
    assert result["cheap_scanned_count"] == 31
    assert result["fast_analysed_count"] <= 10
    assert result["rows"]
    assert result["rows"][0]["title"] == "Upper Deck Young Guns Rookie"
    assert all(row.get("seller_alias") == "Etanol71" for row in result["rows"])


def test_triage_returns_no_inventory_for_wrong_seller():
    result = build_seller_inventory_triage(
        "NoSuchSeller",
        [{"titel": "Card", "pris": 10, "saljare": "Etanol71"}],
        analyze_fn=_fake_analyze,
    )
    assert result["status"] == "NO_INVENTORY"
    assert result["rows"] == []
