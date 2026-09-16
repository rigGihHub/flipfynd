"""Completed full analysis must never be replaced by an older fast result."""
from src.seller_top5 import build_seller_top5


def _item(item_id="one"):
    return {
        "titel": "2023-24 Upper Deck Hockey Connor McDavid #1",
        "lank": f"https://www.tradera.com/item/2933/{item_id}",
        "pris": 100,
    }


def _analyze(item, mode="fast", **kwargs):
    fast = mode == "fast"
    return {
        "beslut": "UNDERSÖK" if fast else "SKIP",
        "exact_identity_gate_supports_exact_comp_search": fast,
        "sold_comparable_count": 0,
        "rank_score": 80 if fast else 1,
        "risk_adjusted_profit": 80 if fast else -90,
    }


def test_successful_full_rejection_does_not_resurrect_fast_research():
    result = build_seller_top5("seller", [_item()], analyze_fn=_analyze)
    assert result["full_analysed"] == 1
    assert result["failed_full"] == 0
    assert result["rows"] == []
    assert result["status"] == "NO_CARD_CANDIDATES"


def test_full_enriched_listing_id_still_suppresses_original_fast_row():
    def analyze(item, mode="fast", **kwargs):
        result = _analyze(item, mode=mode, **kwargs)
        if mode == "full":
            result["tradera_item_id"] = "enriched-id"
        return result

    result = build_seller_top5("seller", [_item()], analyze_fn=analyze)
    assert result["full_analysed"] == 1
    assert result["rows"] == []


def test_actual_full_failure_keeps_preliminary_fallback():
    def analyze(item, mode="fast", **kwargs):
        if mode == "full":
            raise RuntimeError("Temporary unavailable provider")
        return _analyze(item, mode=mode, **kwargs)

    result = build_seller_top5("seller", [_item()], analyze_fn=analyze)
    assert result["full_analysed"] == 0
    assert result["failed_full"] == 1
    assert len(result["rows"]) == 1
    assert result["rows"][0]["analysis_level"] == "quick_fallback"


def test_unanalyzed_listing_keeps_fallback_even_for_same_card(monkeypatch):
    # A different asking price can make another listing worth checking. Do not
    # turn a per-listing rejection into a blanket rejection of that identity.
    monkeypatch.setattr(
        "src.seller_top5.select_dynamic_seller_deep_rows",
        lambda rows, **kwargs: rows[:1],
    )
    second = {**_item("two"), "pris": 10}
    def analyze(item, mode="fast", **kwargs):
        result = _analyze(item, mode=mode, **kwargs)
        if mode == "fast":
            result["rank_score"] = item["pris"]
        return result

    result = build_seller_top5("seller", [_item(), second], analyze_fn=analyze)
    assert result["full_analysed"] == 1
    assert result["failed_full"] == 0
    assert len(result["rows"]) == 1
    assert result["rows"][0]["analysis_level"] == "quick_fallback"
    assert result["rows"][0]["price"] == 10
    assert result["rows"][0]["url"] == second["lank"]


def test_presentable_full_result_keeps_full_economics():
    item = {**_item(), "titel": "2023-24 Upper Deck Hockey Connor McDavid 7/25 #1"}
    result = build_seller_top5("seller", [item], analyze_fn=_analyze)
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["analysis_level"] == "full"
    assert row["decision"] == "SKIP"
    assert row["risk_adjusted_profit"] == -90
