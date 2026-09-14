from src.seller_top5 import build_seller_top5


def _fake_analyze(item, mode="fast", strategy_mode=None, sport=None, all_items=None):
    title = item.get("titel", "")
    base = {
        "titel": title,
        "lank": item.get("lank"),
        "pris": item.get("pris", 0),
        "exact_identity_gate_supports_exact_comp_search": item.get("identity_ok", True),
        "exact_identity_gate_score": 90 if item.get("identity_ok", True) else 20,
        "valuation_confidence_score": item.get("valuation", 60),
        "market_edge_score": item.get("edge", 0),
        "sold_comparable_count": item.get("sold", 0),
        "rank_score": item.get("rank", 50),
        "player_market_score": item.get("player_market", 0),
        "risk_adjusted_profit": item.get("profit", 0),
        "beslut": item.get("decision", "SKIP"),
    }
    return base


def test_returns_five_when_five_card_candidates_exist():
    items = [
        {"titel": f"Card {i}", "lank": f"u{i}", "pris": 10 + i, "rank": 30 + i}
        for i in range(12)
    ]
    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze, quick_limit=12, full_limit=10)
    assert out["status"] == "READY"
    assert len(out["rows"]) == 5


def test_skip_rows_can_fill_top5_without_becoming_find_signals():
    items = [
        {"titel": f"Weak card {i}", "lank": f"w{i}", "pris": 10 + i, "rank": 20 + i, "decision": "SKIP"}
        for i in range(12)
    ]
    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze, quick_limit=12, full_limit=10)
    assert out["status"] == "READY"
    assert len(out["rows"]) == 5
    assert all(str(row["decision"]).upper().startswith("SKIP") for row in out["rows"])
    assert all(row["label"] == "BÄST AV RESTEN" for row in out["rows"])


def test_ordinary_zero_comp_undersok_is_returned_but_not_upgraded_to_buy():
    items = [{
        "titel": "1986-87 Kraft Dan Daoust", "lank": "dan", "pris": 87,
        "edge": 20, "sold": 0, "valuation": 25, "decision": "UNDERSÖK", "rank": 35,
    }]
    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze)
    assert out["status"] == "READY"
    assert len(out["rows"]) == 1
    assert out["rows"][0]["decision"] == "UNDERSÖK"
    assert out["rows"][0]["label"] == "VÄRT ATT UNDERSÖKA"


def test_ordinary_final_rank_order_is_reused_exactly():
    items = [
        {"titel": "A", "lank": "a", "rank": 80, "player_market": 20, "profit": 100, "decision": "SKIP"},
        {"titel": "B", "lank": "b", "rank": 80, "player_market": 70, "profit": 10, "decision": "SKIP"},
        {"titel": "C", "lank": "c", "rank": 80, "player_market": 70, "profit": 200, "decision": "SKIP"},
        {"titel": "D", "lank": "d", "rank": 90, "player_market": 0, "profit": 0, "decision": "SKIP"},
        {"titel": "E", "lank": "e", "rank": 70, "player_market": 100, "profit": 999, "decision": "KÖP"},
    ]
    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze)
    assert [row["title"] for row in out["rows"]] == ["D", "C", "B", "A", "E"]
    assert out["ranking_source"] == "ORDINARY_FLIPFYND_RANK"


def test_verified_buy_ranks_before_equal_rank_skip_via_quick_preselection_stability():
    items = [
        {"titel": "Cheap base", "lank": "a", "pris": 5, "edge": 10, "sold": 0, "decision": "SKIP", "rank": 50},
        {"titel": "Real deal", "lank": "b", "pris": 100, "edge": 70, "sold": 2, "decision": "KÖP", "rank": 50},
    ]
    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze, quick_limit=10, full_limit=10)
    assert out["rows"][0]["title"] == "Real deal"


def test_empty_inventory_is_explicit():
    out = build_seller_top5("seller1", [], analyze_fn=_fake_analyze)
    assert out["status"] == "NO_ITEMS"
    assert out["rows"] == []


def test_large_inventory_scans_beyond_first_batch():
    items = [
        {"titel": f"Base {i}", "lank": f"u{i}", "pris": 20 + i, "edge": 5, "sold": 0, "decision": "SKIP", "rank": 10}
        for i in range(130)
    ]
    items[-1].update({"titel": "Late hidden deal", "edge": 95, "sold": 3, "decision": "KÖP", "rank": 95})

    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze, quick_limit=40, full_limit=10)

    assert out["status"] == "READY"
    assert out["rows"][0]["title"] == "Late hidden deal"
    assert out["quick_batches"] >= 4
    assert out["quick_analysed"] == 130
    assert out["coverage_complete"] is True
    assert out["full_candidate_limit"] >= 20


def test_duplicate_inventory_rows_are_only_quick_scanned_once():
    items = [
        {"titel": "A", "lank": "same", "pris": 10, "edge": 10, "sold": 0},
        {"titel": "A duplicate", "lank": "same", "pris": 10, "edge": 10, "sold": 0},
        {"titel": "B", "lank": "b", "pris": 20, "edge": 20, "sold": 1},
    ]
    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze, quick_limit=20, full_limit=5)
    assert out["inventory_count"] == 3
    assert out["inventory_unique_count"] == 2
    assert out["quick_analysed"] == 2
