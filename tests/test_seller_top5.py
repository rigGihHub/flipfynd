from src.seller_top5 import build_seller_top5


def _fake_analyze(item, mode="fast", strategy_mode=None, sport=None, all_items=None):
    title = item.get("titel", "")
    base = {
        "titel": title,
        "lank": item.get("lank"),
        "pris": item.get("pris", 0),
        "exact_identity_gate_supports_exact_comp_search": True,
        "exact_identity_gate_score": 90,
        "valuation_confidence_score": 60,
        "market_edge_score": item.get("edge", 0),
        "sold_comparable_count": item.get("sold", 0),
        "rank_score": item.get("rank", 50),
        "beslut": item.get("decision", "SKIP"),
    }
    return base


def test_returns_at_most_five_rows():
    items = [
        {"titel": f"Card {i}", "lank": f"u{i}", "pris": 10 + i, "edge": 20 + i, "sold": i % 3}
        for i in range(12)
    ]
    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze, quick_limit=12, full_limit=10)
    assert out["status"] == "READY"
    assert len(out["rows"]) == 5


def test_verified_buy_ranks_before_unverified_skip():
    items = [
        {"titel": "Cheap base", "lank": "a", "pris": 5, "edge": 10, "sold": 0, "decision": "SKIP"},
        {"titel": "Real deal", "lank": "b", "pris": 100, "edge": 70, "sold": 2, "decision": "KÖP"},
    ]
    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze, quick_limit=10, full_limit=10)
    assert out["rows"][0]["title"] == "Real deal"


def test_empty_inventory_is_explicit():
    out = build_seller_top5("seller1", [], analyze_fn=_fake_analyze)
    assert out["status"] == "NO_ITEMS"
    assert out["rows"] == []
