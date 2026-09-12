from src.seller_live_quick_analysis import quick_analyze_seller_inventory


def fake_analyze(item, mode="fast", strategy_mode="quick_flip", sport="hockey"):
    title = item.get("titel", "")
    if "Strong" in title:
        return {
            "beslut": "KÖP",
            "exact_identity_gate_supports_exact_comp_search": True,
            "exact_identity_gate_score": 92,
            "sold_comparable_count": 3,
            "valuation_confidence_score": 82,
            "rank_score": 77,
            "market_edge_score": 65,
        }
    if "Review" in title:
        return {
            "beslut": "SKIP",
            "exact_identity_gate_supports_exact_comp_search": False,
            "exact_identity_gate_score": 61,
            "sold_comparable_count": 0,
            "valuation_confidence_score": 20,
            "rank_score": 72,
            "market_edge_score": 15,
        }
    return {
        "beslut": "SKIP",
        "exact_identity_gate_supports_exact_comp_search": False,
        "exact_identity_gate_score": 20,
        "sold_comparable_count": 0,
        "valuation_confidence_score": 10,
        "rank_score": 25,
        "market_edge_score": 0,
    }


def test_quick_analysis_prioritises_evidence_backed_candidate():
    anchor = {"tradera_item_id": "1", "titel": "Anchor", "pris": 100}
    items = [
        {"tradera_item_id": "2", "titel": "Weak card", "pris": 20},
        {"tradera_item_id": "3", "titel": "Strong #99 Upper Deck", "pris": 80},
        {"tradera_item_id": "4", "titel": "Review Topps Chrome", "pris": 50},
    ]
    out = quick_analyze_seller_inventory(anchor, items, analyze_fn=fake_analyze, limit=20, shortlist=5)
    assert out["status"] == "READY"
    assert out["analysed_count"] == 3
    assert out["shortlist"][0]["title"].startswith("Strong")
    assert out["shortlist"][0]["label"] == "STARK KANDIDAT"
    assert out["shortlist"][0]["sold_comps"] == 3


def test_anchor_is_excluded_and_shortlist_is_capped_at_five():
    anchor = {"tradera_item_id": "1", "titel": "Anchor", "pris": 100}
    items = [anchor] + [
        {"tradera_item_id": str(i), "titel": f"Review card {i}", "pris": i}
        for i in range(2, 12)
    ]
    out = quick_analyze_seller_inventory(anchor, items, analyze_fn=fake_analyze, limit=20, shortlist=99)
    assert out["analysed_count"] == 10
    assert len(out["shortlist"]) == 5
    assert all(row["title"] != "Anchor" for row in out["rows"])


def test_star_like_rank_alone_does_not_create_strong_candidate():
    def star_only(item, **kwargs):
        return {
            "beslut": "SKIP",
            "exact_identity_gate_supports_exact_comp_search": False,
            "exact_identity_gate_score": 35,
            "sold_comparable_count": 0,
            "valuation_confidence_score": 10,
            "rank_score": 99,
            "market_edge_score": 0,
        }
    out = quick_analyze_seller_inventory({}, [{"tradera_item_id": "9", "titel": "Wayne Gretzky base", "pris": 10}], analyze_fn=star_only)
    row = out["shortlist"][0]
    assert row["label"] != "STARK KANDIDAT"
    assert row["sold_comps"] == 0
