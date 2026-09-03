from src.information_edge_hunter import build_information_edge_hunter


def test_information_edge_flags_underdescribed_listing_without_creating_value():
    result = build_information_edge_hunter(
        item={"titel": "Hockeykort Bedard", "image_urls": ["x"]},
        features={"identity_enriched_fields": ["parallel", "serial_numbered", "card_number"], "is_lot": False},
        listing_quality={"score": 40},
        hidden_find={"score": 70},
        market_edge={"score": 72},
        visual_edge={"score": 70},
        identity_gate={"status": "GRANSKA"},
    )
    assert result["is_candidate"] is True
    assert result["score"] >= 75
    assert "parallel/variant" in result["verify_first"]
    assert result["can_create_value"] is False
    assert result["can_create_buy_decision"] is False


def test_information_edge_stays_low_for_well_described_listing():
    result = build_information_edge_hunter(
        item={"titel": "2024 Upper Deck Connor Bedard Young Guns #451 Rookie"},
        features={"identity_enriched_fields": [], "is_lot": False},
        listing_quality={"score": 92}, hidden_find={"score": 10}, market_edge={"score": 5},
        visual_edge={"score": 10}, identity_gate={"status": "VERIFIERAD"},
    )
    assert result["is_candidate"] is False
    assert result["score"] < 35


def test_locked_identity_caps_information_edge():
    result = build_information_edge_hunter(
        item={"titel": "Kort lot"},
        features={"identity_enriched_fields": ["parallel", "serial_numbered"], "is_lot": True},
        listing_quality={"score": 20}, hidden_find={"score": 90}, market_edge={"score": 90},
        visual_edge={"score": 90}, identity_gate={"status": "LÅST"},
    )
    assert result["score"] <= 64
    assert result["review_only"] is True
