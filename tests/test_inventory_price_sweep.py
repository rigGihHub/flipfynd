from src.inventory_price_sweep import sweep_inventory
from src.asking_price_opportunity import build_asking_price_opportunity


def test_sweep_reaches_profitable_card_outside_first_160_without_changing_economics():
    rows = [{"id": str(i), "titel": "2023-24 Upper Deck #201 Connor Bedard",
             "pris": 20 if i == 617 else 200, "frakt": 22} for i in range(618)]
    context = {"rows": [{"url": f"https://example.com/{i}", "price": 100,
                         "currency": "SEK", "asking_comparison_eligible": True} for i in range(3)]}
    def enrich(row):
        return {**row, "asking_price_opportunity": build_asking_price_opportunity(row, context)}
    initial = [enrich(row) for row in rows[:124]]
    screened, debug = sweep_inventory([{"source_item": row} for row in rows], initial, enrich)
    assert len(screened) == 494
    assert debug["inventory_price_remaining"] == 0
    positives = [row for row in screened if row["asking_price_opportunity"]["possible_find"]]
    assert [row["id"] for row in positives] == ["617"]
    assert positives[0]["asking_price_opportunity"]["net_margin"] == 31.5
    assert positives[0]["asking_price_opportunity"]["creates_sold_evidence"] is False


def test_rate_limit_stops_after_current_batch_and_reports_unchecked_inventory():
    calls = []
    def enrich(row):
        calls.append(row["id"])
        return {**row, "asking_price_opportunity": {"http_status": 429}}
    rows = [{"id": str(i)} for i in range(20)]
    screened, debug = sweep_inventory(rows, [], enrich, workers=3)
    assert len(calls) == len(screened) == 3
    assert debug["inventory_price_remaining"] == 17
    assert debug["inventory_price_stop"] == "API_LIMIT"


def test_time_and_request_caps_do_not_claim_complete_coverage():
    rows = [{"id": str(i)} for i in range(20)]
    screened, debug = sweep_inventory(rows, [], dict, seconds=0)
    assert screened == []
    assert debug["inventory_price_remaining"] == 20
    assert debug["inventory_price_stop"] == "TIME_LIMIT"
    screened, debug = sweep_inventory(rows, [], dict, limit=5)
    assert len(screened) == 5
    assert debug["inventory_price_remaining"] == 15
    assert debug["inventory_price_stop"] == "REQUEST_LIMIT"
