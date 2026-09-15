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


def test_generic_cards_do_not_fill_top5_without_merit():
    items = [
        {"titel": f"Card {i}", "lank": f"u{i}", "pris": 10 + i, "rank": 30 + i}
        for i in range(12)
    ]
    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze, quick_limit=12, full_limit=10)
    assert out["status"] == "NO_CARD_CANDIDATES"
    assert out["rows"] == []


def test_skip_rows_cannot_fill_top5_without_merit():
    items = [
        {"titel": f"Weak card {i}", "lank": f"w{i}", "pris": 10 + i, "rank": 20 + i, "decision": "SKIP"}
        for i in range(12)
    ]
    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze, quick_limit=12, full_limit=10)
    assert out["status"] == "NO_CARD_CANDIDATES"
    assert out["rows"] == []


def test_serie_nytt_is_never_a_seller_top5_card():
    items = [
        {"titel": "1978 Serie Nytt #11", "lank": "comic", "pris": 20, "rank": 100, "decision": "KÖP"},
        {"titel": "Wayne Gretzky Upper Deck card", "lank": "card", "pris": 50, "rank": 40, "decision": "SKIP"},
    ]
    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze)
    assert all(row["title"] != "1978 Serie Nytt #11" for row in out["rows"])
    assert out["domain_rejected_count"] >= 1


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


def test_buy_evidence_wins_then_ordinary_rank_breaks_equal_opportunity_ties():
    items = [
        {"titel": "A", "lank": "a", "rank": 80, "player_market": 20, "profit": 100, "decision": "SKIP"},
        {"titel": "B", "lank": "b", "rank": 80, "player_market": 70, "profit": 10, "decision": "SKIP"},
        {"titel": "C", "lank": "c", "rank": 80, "player_market": 70, "profit": 200, "decision": "SKIP"},
        {"titel": "D", "lank": "d", "rank": 90, "player_market": 0, "profit": 0, "decision": "SKIP"},
        {"titel": "E", "lank": "e", "rank": 70, "player_market": 100, "profit": 999, "decision": "KÖP"},
    ]
    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze)
    assert [row["title"] for row in out["rows"]] == ["E"]
    assert out["ranking_source"] == "ORDINARY_FLIPFYND_RANK"


def test_fast_preselection_prefers_ordinary_rank_over_cheap_mediocre_card():
    items = [
        {"titel": f"Mediocre card {i}", "lank": f"m{i}", "pris": 5 + i, "rank": 5, "player_market": 5, "profit": 0}
        for i in range(40)
    ]
    items.append({
        "titel": "Elite rookie patch /25", "lank": "elite", "pris": 250,
        "rank": 92, "player_market": 88, "profit": 300, "decision": "UNDERSÖK",
    })
    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze, quick_limit=20, full_limit=10)
    assert out["rows"][0]["title"] == "Elite rookie patch /25"
    assert out["seller_analysis_contract"] == "v3-ordinary-evidence-opportunity-overlay"


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
    # The bounded performance pass no longer needs to analyse all 130 rows, but
    # it must cross the first batch and retain the late hidden opportunity.
    assert out["quick_batches"] >= 2
    assert out["fast_pool_count"] < out["card_inventory_count"]
    assert out["quick_analysed"] == out["fast_pool_count"]
    assert out["coverage_complete"] is True
    assert 1 <= out["full_candidate_limit"] <= 15


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


def test_same_identifiable_card_only_occupies_one_top5_place():
    items = [
        {"titel": "2022-23 Topps UEFA Club Superstars #100 Jamal Musiala Common Yellow Variation", "lank": "a", "rank": 90},
        {"titel": "2022-23 Topps UEFA Club Competitions Superstars Common Yellow Jamal Musiala #100", "lank": "b", "rank": 89},
        {"titel": "2023-24 Upper Deck Dazzlers #DZ-144 Auston Matthews", "lank": "c", "rank": 70},
    ]

    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze)

    musiala_rows = [row for row in out["rows"] if "Musiala" in row["title"]]
    assert len(musiala_rows) <= 1


def test_explicitly_damaged_card_is_ranked_after_clean_alternatives():
    items = [
        {"titel": "2006-07 Fleer Speed Machines 7/99 #SM8 Joe Sakic Märken på ovandelen", "lank": "damaged", "rank": 99},
        *[
            {"titel": f"2023-24 Upper Deck Hockey Card {i}/99 #{i} Player Name{i}", "lank": f"clean-{i}", "rank": 80 - i}
            for i in range(1, 6)
        ],
    ]

    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze)

    assert all("Märken på" not in row["title"] for row in out["rows"])
    assert out["condition_risks_demoted"] >= 1


def test_card_specific_rarity_beats_common_star_base_when_evidence_tier_is_equal():
    items = [
        {
            "titel": "2022-23 Topps Common Base Superstar #100 Famous Player",
            "lank": "base",
            "rank": 65,
            "decision": "SKIP",
        },
        {
            "titel": "2021 Donruss Elite Rookie Orange 7/75 #185 Young Prospect RC",
            "lank": "rare",
            "rank": 50,
            "decision": "SKIP",
        },
    ]

    out = build_seller_top5("seller1", items, analyze_fn=_fake_analyze)

    assert out["rows"][0]["title"].startswith("2021 Donruss Elite Rookie Orange 7/75")
    # Rarity keeps this ahead of a common base card for research, but cannot
    # inflate it into strong economic opportunity without comps or margin.
    assert out["rows"][0]["seller_opportunity_score"] <= 25
