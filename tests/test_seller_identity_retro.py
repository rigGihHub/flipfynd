from src.seller_identity import (
    backfill_seller_metadata,
    recover_seller_from_market,
    seller_alias,
    seller_id,
    seller_url,
)


def test_nested_seller_metadata_is_recovered():
    item = {
        "id": "123",
        "seller": {
            "Alias": "Etanol71",
            "Id": 42,
            "Url": "https://www.tradera.com/profile/Etanol71",
        },
    }
    assert seller_alias(item) == "Etanol71"
    assert seller_id(item) == "42"
    assert seller_url(item).endswith("/Etanol71")


def test_old_listing_gets_retroactive_seller_metadata_from_same_listing():
    old = {"id": "123", "titel": "Rare card", "pris": 100}
    enriched_copy = {
        "id": "123",
        "titel": "Rare card",
        "pris": 100,
        "seller": {
            "Alias": "Etanol71",
            "Id": 42,
            "Url": "https://www.tradera.com/profile/Etanol71",
        },
    }
    enriched = backfill_seller_metadata([old, enriched_copy])[0]
    assert enriched["seller_alias"] == "Etanol71"
    assert enriched["saljare_alias"] == "Etanol71"
    assert enriched["seller_id"] == "42"
    assert enriched["seller_url"].endswith("/Etanol71")


def test_backfill_does_not_join_different_listing():
    old = {"id": "999", "titel": "Rare card", "pris": 101}
    other = {
        "id": "123",
        "titel": "Rare card",
        "pris": 100,
        "seller_alias": "Etanol71",
    }
    enriched = backfill_seller_metadata([old, other])[0]
    assert "seller_alias" not in enriched


def test_market_recovery_returns_canonical_seller_metadata():
    market_item = {
        "id": "123",
        "seller": {"Alias": "Etanol71", "Id": 42},
    }
    alias, merged = recover_seller_from_market({"id": "123"}, [market_item])
    assert alias == "Etanol71"
    assert merged["seller_alias"] == "Etanol71"
    assert merged["seller_id"] == "42"
