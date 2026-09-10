from src.sold_research_assist import (
    build_exact_research_query,
    ebay_sold_search_url,
    build_manual_sold_row,
)
from src.sold_acquisition_pipeline import acquire_sold_batch


IDENTITY = {
    "player_name": "Connor McDavid",
    "set_name": "Upper Deck",
    "season": "2025-26",
    "card_number": "97",
    "parallel": "Silver",
}


def test_exact_query_uses_only_structured_identity():
    out = build_exact_research_query(IDENTITY)
    assert out["ready"] is True
    assert out["query"] == "Connor McDavid Upper Deck 2025-26 #97 Silver"


def test_exact_query_fails_closed_when_core_identity_missing():
    out = build_exact_research_query({"player_name": "Connor McDavid"})
    assert out["ready"] is False
    assert set(out["missing_fields"]) == {"set_name", "season", "card_number"}


def test_ebay_url_is_sold_and_completed_search():
    url = ebay_sold_search_url(IDENTITY)
    assert "LH_Sold=1" in url
    assert "LH_Complete=1" in url
    assert "Connor+McDavid" in url


def test_manual_sale_requires_explicit_confirmation():
    try:
        build_manual_sold_row(
            IDENTITY,
            sold_price=100,
            currency="SEK",
            source_platform="eBay",
            sale_confirmed=False,
        )
    except ValueError as exc:
        assert "verifierad" in str(exc)
    else:
        raise AssertionError("unconfirmed sale must be rejected")


def test_non_sek_requires_explicit_fx_rate():
    try:
        build_manual_sold_row(
            IDENTITY,
            sold_price=20,
            currency="USD",
            source_platform="eBay",
            sale_confirmed=True,
        )
    except ValueError as exc:
        assert "fx_rate_to_sek" in str(exc)
    else:
        raise AssertionError("foreign currency without explicit FX must be rejected")


def test_confirmed_identity_sale_can_enter_exact_ready_pipeline():
    row = build_manual_sold_row(
        IDENTITY,
        sold_price=125,
        currency="SEK",
        source_platform="eBay",
        sold_url="https://example.com/sale",
        sold_at="2026-09-08",
        identity_verified=True,
        identity_evidence_source="manual image + checklist review",
        sale_confirmed=True,
    )
    result = acquire_sold_batch([row], existing=[], source_key="manual_research_assist", batch_id="test")
    assert result["added_count"] == 1
    assert result["exact_ready_count"] == 1
