from src.seller_collector_signals import collector_signals
from src.seller_live_quick_analysis import quick_analyze_seller_inventory


def _fake_analyze(item, mode="fast", strategy_mode=None, sport=None):
    return {
        "titel": item.get("titel"),
        "lank": item.get("lank"),
        "pris": item.get("pris", 0),
        "exact_identity_gate_supports_exact_comp_search": False,
        "exact_identity_gate_score": 30,
        "valuation_confidence_score": 20,
        "market_edge_score": 10,
        "rank_score": 20,
        "sold_comparable_count": 0,
        "beslut": "SKIP",
    }


def test_serial_patch_rookie_gets_strong_research_signal():
    out = collector_signals({"titel": "Connor Bedard Rookie Patch Auto 12/25"})
    assert out["score"] >= 30
    assert "rookie" in out["signals"]
    assert "patch_relic" in out["signals"]
    assert "autograph" in out["signals"]
    assert "serial_numbered" in out["signals"]


def test_signature_style_and_silver_script_are_not_auto_signals():
    for title in ("Signature Style Connor McDavid", "Silver Script Sidney Crosby"):
        out = collector_signals({"titel": title})
        assert "autograph" not in out["signals"]


def test_error_and_case_hit_are_prioritized():
    out = collector_signals({"titel": "Rare Error Variation Case Hit"})
    assert "error_variation" in out["signals"]
    assert "case_hit_ssp" in out["signals"]


def test_value_driver_listing_is_selected_before_plain_base_when_limit_is_tight():
    rows = [
        {"titel": "1988 Player Base Card", "lank": "base", "pris": 5},
        {"titel": "2024 Rookie Patch Auto 7/25", "lank": "rare", "pris": 200},
    ]
    out = quick_analyze_seller_inventory(
        {"saljare": "seller", "tradera_item_id": "anchor"},
        rows,
        analyze_fn=_fake_analyze,
        limit=1,
        shortlist=1,
    )
    assert out["analysed_count"] == 1
    assert out["rows"][0]["title"] == "2024 Rookie Patch Auto 7/25"
    assert out["rows"][0]["collector_signal_score"] > 0
