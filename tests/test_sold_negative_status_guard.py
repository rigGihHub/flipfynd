import pytest

from src.external_sold_sources import adapt_external_rows
from src.sold_comp_collector import collect_sold_comps, has_explicit_sold_evidence
from src.sold_comp_import import import_sold_comp_rows, normalize_sold_comp


def test_collector_rejects_unsold_even_when_word_contains_sold():
    row = {"titel": "Card", "price": 100, "status": "unsold"}
    assert has_explicit_sold_evidence(row) is False

    out = collect_sold_comps([row])
    assert out["candidate_count"] == 0
    assert out["added_count"] == 0
    assert out["rejection_reasons"]["explicit_unsold_state"] == 1


def test_collector_rejects_not_sold_with_explicit_sold_price_field():
    row = {"titel": "Card", "sold_price": 100, "sale_status": "not sold"}
    assert has_explicit_sold_evidence(row) is False

    out = collect_sold_comps([row])
    assert out["candidate_count"] == 0
    assert out["rejection_reasons"]["explicit_unsold_state"] == 1


def test_collector_accepts_normalized_completed_sold_state_with_price():
    row = {"titel": "Card", "price": 100, "status": "completed_sold"}
    assert has_explicit_sold_evidence(row) is True


def test_external_adapter_rejects_unsold_substring_trap():
    out = adapt_external_rows(
        [{"title": "Card", "price": 100, "status": "unsold"}],
        "generic",
    )
    assert out["adapted_count"] == 0
    assert out["rejected_count"] == 1
    assert out["rejected"][0]["reason"] == "explicit_unsold_state"


def test_external_adapter_rejects_false_sold_flag_even_with_sold_status():
    out = adapt_external_rows(
        [{"title": "Card", "price": 100, "status": "sold", "sold": False}],
        "generic",
    )
    assert out["adapted_count"] == 0
    assert out["rejected"][0]["reason"] == "explicit_unsold_state"


def test_external_adapter_accepts_explicit_completed_sold_status():
    out = adapt_external_rows(
        [{"title": "Card", "price": 100, "status": "completed_sold"}],
        "generic",
    )
    assert out["adapted_count"] == 1
    assert out["rows"][0]["sale_status"] == "sold"


def test_central_normalizer_rejects_unsold_despite_positive_sold_price():
    with pytest.raises(ValueError, match="osåld/aktiv/avbruten"):
        normalize_sold_comp({"title": "Card sale", "sold_price": 100, "status": "unsold"})


def test_central_normalizer_rejects_active_listing_despite_sold_price_field():
    out = import_sold_comp_rows([
        {"title": "Card sale", "sold_price": 100, "market_state": "active"}
    ])
    assert out["valid_count"] == 0
    assert out["added_count"] == 0
    assert out["error_count"] == 1


def test_central_normalizer_still_accepts_sold_price_when_no_contradiction_exists():
    row = normalize_sold_comp({"title": "Card sale", "sold_price": 100})
    assert row["market_state"] == "sold"
    assert row["sold_price"] == 100
