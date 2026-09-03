import pytest

from src.external_sold_sources import adapt_external_rows, import_external_sold_rows


def test_ended_is_not_sold_without_explicit_sold_marker():
    result = adapt_external_rows([{"title": "Card X", "price": 100, "status": "ended"}], "generic")
    assert result["adapted_count"] == 0
    assert result["rejected_count"] == 1


def test_ebay_completed_status_is_accepted_then_strictly_normalized():
    result = import_external_sold_rows([{
        "title": "2024 Topps Chrome Player Auto /99",
        "price": 250,
        "currency": "SEK",
        "status": "completed",
        "url": "https://example.test/item/1",
    }], "ebay")
    assert result["added_count"] == 1
    row = result["records"][0]
    assert row["sold_price"] == 250
    assert row["provenance"] == "external_adapter:ebay"
    assert row["sold_verification_status"] == "verified"


def test_foreign_currency_without_fx_is_rejected_by_existing_gate():
    result = import_external_sold_rows([{
        "title": "2024 Upper Deck Young Guns Player",
        "price": 20,
        "currency": "USD",
        "sold": True,
    }], "ebay")
    assert result["added_count"] == 0
    assert result["error_count"] == 1
    assert "valuta USD" in result["errors"][0]["error"]


def test_foreign_currency_with_explicit_fx_is_allowed():
    result = import_external_sold_rows([{
        "title": "2024 Upper Deck Young Guns Player",
        "price": 20,
        "currency": "USD",
        "fx_rate_to_sek": 10,
        "sold": True,
    }], "ebay")
    assert result["added_count"] == 1
    assert result["records"][0]["sold_price"] == 200


def test_unknown_adapter_fails_closed():
    with pytest.raises(ValueError):
        adapt_external_rows([], "mystery")
