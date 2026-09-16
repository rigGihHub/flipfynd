"""Ambiguous exports must not acquire verified SOLD provenance during import."""
import pytest

from src.external_sold_sources import import_external_sold_rows
from src.market_analysis import build_market_analysis
from src.sold_comp_import import normalize_sold_comp
from src.sold_comp_quality import is_verified_sold_comp


@pytest.mark.parametrize("status", [None, "ended", "completed", "closed"])
@pytest.mark.parametrize("price_field", ["price", "pris"])
def test_generic_price_requires_explicit_sale_evidence(status, price_field):
    with pytest.raises(ValueError, match="explicit såld"):
        normalize_sold_comp({"title": "Connor McDavid card", price_field: 100, "status": status})


@pytest.mark.parametrize("evidence", [
    {"sold": True}, {"is_sold": "yes"}, {"status": "sold"},
    {"sale_status": "completed_sold"}, {"state": "avslutad såld"},
])
def test_confirmed_sale_with_generic_price_remains_usable(evidence):
    row = normalize_sold_comp({"title": "Connor McDavid card", "price": 100, **evidence})
    assert row["sale_evidence_type"] == "explicit_sold_state_and_price"
    assert is_verified_sold_comp(row)


@pytest.mark.parametrize("field", ["sold_price", "soldprice"])
def test_explicit_sold_price_contract_remains_supported(field):
    row = normalize_sold_comp({"title": "Connor McDavid card", field: 100})
    assert row["sale_evidence_type"] == "explicit_sold_price"
    assert is_verified_sold_comp(row)


@pytest.mark.parametrize("status_field", ["sale_status", "status", "listing_status", "state", "market_state"])
@pytest.mark.parametrize("negative", ["active", "unsold", "cancelled"])
def test_adapter_checks_every_status_before_stripping_source_fields(status_field, negative):
    row = {"title": "Connor McDavid card", "price": 100, "sold": True, "sale_status": "sold"}
    row[status_field] = negative
    result = import_external_sold_rows([row], "ebay")
    assert result["added_count"] == 0
    assert result["adapter_rejected_count"] == 1


@pytest.mark.parametrize("negative", [False, 0, 0.0, "0", "no"])
def test_normalizer_checks_later_conflicting_sold_flags(negative):
    with pytest.raises(ValueError, match="osåld/aktiv/avbruten"):
        normalize_sold_comp({"title": "Connor McDavid card", "sold_price": 100, "sold": True, "was_sold": negative})
    result = import_external_sold_rows([
        {"title": "Connor McDavid card", "price": 100, "sold": True, "was_sold": negative},
    ], "ebay")
    assert result["added_count"] == 0
    assert result["adapter_rejected_count"] == 1


def test_completed_exports_do_not_reach_market_valuation_as_sold():
    title = "2023-24 Upper Deck Connor McDavid #100"
    result = import_external_sold_rows([
        {"title": title, "price": 1000, "status": "completed", "url": f"https://example.test/{i}"}
        for i in range(3)
    ], "ebay")
    assert result["added_count"] == 0
    assert result["adapter_rejected_count"] == 3
    analysis = build_market_analysis({"titel": title, "pris": 70, "frakt": 29}, result["records"])
    assert analysis["sold_comparable_count"] == 0
    assert analysis["valuation_basis"] == "none"


def test_completed_with_independent_positive_sale_flag_remains_accepted():
    result = import_external_sold_rows([
        {"title": "Connor McDavid card", "price": 100, "status": "completed", "sold": True},
    ], "ebay")
    assert result["added_count"] == 1
