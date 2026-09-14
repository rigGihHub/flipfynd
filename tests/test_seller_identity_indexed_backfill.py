from src.seller_identity import backfill_seller_metadata, seller_alias


def test_indexed_backfill_recovers_same_listing_by_id():
    rows = [
        {"tradera_item_id": "123", "titel": "Card", "pris": 10},
        {"tradera_item_id": "123", "titel": "Card", "pris": 10, "saljare": "Etanol71"},
    ]
    out = backfill_seller_metadata(rows)
    assert seller_alias(out[0]) == "Etanol71"


def test_title_price_fallback_refuses_conflicting_sellers():
    rows = [
        {"titel": "Same card", "pris": 25},
        {"titel": "Same card", "pris": 25, "saljare": "SellerA"},
        {"titel": "Same card", "pris": 25, "saljare": "SellerB"},
    ]
    out = backfill_seller_metadata(rows)
    assert seller_alias(out[0]) is None


def test_existing_seller_is_never_overwritten():
    rows = [
        {"tradera_item_id": "1", "titel": "Card", "pris": 5, "saljare": "Original"},
        {"tradera_item_id": "1", "titel": "Card", "pris": 5, "saljare": "Other"},
    ]
    out = backfill_seller_metadata(rows)
    assert seller_alias(out[0]) == "Original"
    assert seller_alias(out[1]) == "Other"
