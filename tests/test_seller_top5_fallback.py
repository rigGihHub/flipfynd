from src.seller_top5_fallback import build_local_seller_top5, local_inventory_for_seller


def _fake_analyze(item, mode="fast", strategy_mode=None, sport=None, all_items=None):
    return {
        "titel": item.get("titel") or item.get("title") or "",
        "lank": item.get("lank") or item.get("url"),
        "pris": item.get("pris") or item.get("price") or 0,
        "exact_identity_gate_supports_exact_comp_search": True,
        "exact_identity_gate_score": 90,
        "valuation_confidence_score": 60,
        "market_edge_score": item.get("edge", 20),
        "sold_comparable_count": item.get("sold", 1),
        "rank_score": 60,
        "beslut": item.get("decision", "UNDERSÖK"),
    }


def test_local_inventory_matches_alias_case_insensitively_but_not_partially():
    rows = [
        {"titel": "A", "pris": 10, "saljare": "Etanol71"},
        {"titel": "B", "pris": 20, "seller": {"alias": "etanol71"}},
        {"titel": "C", "pris": 30, "saljare": "Etanol710"},
        {"titel": "D", "pris": 40, "saljare": "OtherSeller"},
    ]

    inventory = local_inventory_for_seller("ETANOL71", rows)

    assert [row["titel"] for row in inventory] == ["A", "B"]


def test_local_inventory_can_use_backfilled_seller_metadata_for_same_listing():
    rows = [
        {"tradera_item_id": "123", "titel": "Card", "pris": 99},
        {"tradera_item_id": "123", "titel": "Card", "pris": 99, "seller": {"alias": "Etanol71", "id": 77}},
    ]

    inventory = local_inventory_for_seller("Etanol71", rows)

    assert len(inventory) == 2
    assert all(row.get("seller_alias") == "Etanol71" for row in inventory)


def test_local_inventory_does_not_guess_seller_from_title_or_similarity():
    rows = [
        {"titel": "Etanol71 hockeykort", "pris": 10},
        {"titel": "Card", "pris": 20, "saljare": "Etanol7"},
    ]

    assert local_inventory_for_seller("Etanol71", rows) == []


def test_build_local_seller_top5_reports_local_source_and_counts():
    rows = [
        {"titel": "Deal", "lank": "u1", "pris": 50, "saljare": "Etanol71", "sold": 2, "edge": 70, "decision": "KÖP"},
        {"titel": "Other", "lank": "u2", "pris": 30, "saljare": "OtherSeller"},
    ]

    out = build_local_seller_top5("Etanol71", rows, analyze_fn=_fake_analyze)

    assert out["inventory_source"] == "LOCAL_MARKET"
    assert out["local_market_count"] == 2
    assert out["local_seller_match_count"] == 1
    assert out["inventory_count"] == 1
    assert out["rows"][0]["title"] == "Deal"


def test_build_local_seller_top5_is_explicit_when_no_local_match_exists():
    out = build_local_seller_top5(
        "Etanol71",
        [{"titel": "Other", "saljare": "SomeoneElse", "pris": 10}],
        analyze_fn=_fake_analyze,
    )

    assert out["status"] == "NO_ITEMS"
    assert out["inventory_source"] == "LOCAL_MARKET"
    assert out["local_seller_match_count"] == 0
