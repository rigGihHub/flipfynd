from datetime import datetime, timezone, timedelta
from src.tradera_price_context import screen_tradera_prices

NOW = datetime(2026, 9, 29, 12, tzinfo=timezone.utc)
TITLE = "2023-24 Upper Deck #451 Connor Bedard"


def row(i, price, title=TITLE, **kwargs):
    return {"titel": title, "pris": price, "frakt": 22, "sale_type": "Köp nu",
            "lank": f"https://www.tradera.com/item/293316/{i}/card", "latest_scan_at": NOW.isoformat(), **kwargs}


def test_local_inventory_can_find_one_krona_without_ebay():
    target = row(1, 50.5)
    results, debug = screen_tradera_prices([target], [target, row(2, 100), row(3, 100)], now=NOW)
    assert len(results) == debug["tradera_possible_finds"] == 1
    scenario = results[0]["asking_price_opportunity"]
    assert scenario["net_margin"] == 1
    assert scenario["comparison_count"] == 2
    assert scenario["source_label"] == "Tradera"
    assert not scenario["creates_sold_evidence"]


def test_local_comparisons_exclude_self_duplicates_auctions_stale_wrong_card_and_variants():
    target = row(1, 10)
    comps = [target, target, row(2, 200, TITLE + " Auto"), row(3, 200, TITLE.replace("451", "452")),
             row(4, 200, TITLE.replace("Connor Bedard", "Connor McDavid")),
             row(5, 200, sale_type="Auktion"),
             row(6, 200, latest_scan_at=(NOW-timedelta(days=2)).isoformat()),
             row(7, 200, latest_scan_at=None), row(8, 200, sold=True)]
    results, debug = screen_tradera_prices([target], comps, now=NOW)
    assert results == []
    assert debug["tradera_price_usable"] == 0


def test_one_local_comparison_is_only_a_research_lead_and_lists_sort_by_net():
    first, second = row(1, 10), row(2, 20)
    results, debug = screen_tradera_prices([second, first], [row(3, 100)], now=NOW)
    assert [r["pris"] for r in results] == [10, 20]
    assert debug["tradera_possible_finds"] == 0
    assert all(r["asking_price_opportunity"]["status"] == "RESEARCH_SINGLE_ACTIVE" for r in results)
