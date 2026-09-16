import pytest

from src.analyzer import analyze_item_full
from src.market_analysis import assess_comp_compatibility, build_market_analysis


TITLE = "2023-24 Upper Deck Connor Bedard Young Guns #451"


def listing(suffix="", **fields):
    return {"titel": TITLE + suffix, "pris": 100, "frakt": 20, "lank": "target", **fields}


def sale(suffix="", **fields):
    return listing(
        suffix, pris=1000, sold_price=1000, lank="sale",
        market_state="sold", sold_verification_status="verified",
        sale_evidence_type="explicit_sold_price", sold_at="2026-09-15",
        source_platform="ebay", **fields,
    )


@pytest.mark.parametrize("target,comp", [
    (listing(), sale(" PSA 10")),
    (listing(" PSA 10"), sale()),
    (listing(" PSA 10"), sale(" BGS 10")),
    (listing(" PSA 10"), sale(" PSA 9")),
    (listing(" PSA 10"), sale(" PSA")),
    (listing(" PSA"), sale(" PSA")),
    (listing(), sale(grading_company="PSA", grade=10)),
    (listing(grading_company="PSA", grade=10), sale()),
    (listing(), sale(is_graded=True)),
    (listing(" PSA 10"), sale(" PSA 10", is_graded=False)),
    (listing(" PSA 10"), sale(" PSA 10", grading_company="BGS")),
    (listing(" PSA 10"), sale(" PSA 10", grade=9)),
])
def test_incompatible_or_unresolved_grading_cannot_supply_price_support(target, comp):
    assert assess_comp_compatibility(target, comp)["eligible"] is False
    market = build_market_analysis(target, [comp])
    assert market["sold_comparable_count"] == 0


@pytest.mark.parametrize("target,comp", [
    (listing(), sale()),
    (listing(" PSA 10"), sale(" PSA 10")),
    (listing(" BGS 9.5"), sale(" BGS 9.5")),
    (listing(" PSA 10"), sale(grading_company="PSA", grade=10)),
    (listing(grading_company="PSA", grade="10.0"), sale(" PSA 10")),
    (listing(is_graded=False), sale(is_graded="false")),
])
def test_matching_grading_and_ungraded_research_are_preserved(target, comp):
    assert assess_comp_compatibility(target, comp)["eligible"] is True


def test_full_analyzer_does_not_use_psa10_sales_to_value_raw_young_guns():
    target = listing()
    comps = [sale(" PSA 10"), {**sale(" PSA 10"), "lank": "sale2", "sold_at": "2026-09-14"}]
    result = analyze_item_full(target, all_items=comps, sport="hockey")
    assert result["sold_comparable_count"] == 0
    assert result["value_source"] != "blended_sold_comps"
    assert result["rejected_comparable_count"] == 2
