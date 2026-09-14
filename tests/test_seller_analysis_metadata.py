from src.seller_live_full_analysis import full_analyze_live_seller_item
from src.seller_live_quick_analysis import quick_analyze_seller_inventory


def _fake_analyze(item, mode="fast", strategy_mode=None, sport=None, all_items=None):
    return {
        "titel": item.get("titel") or "Card",
        "pris": item.get("pris", 50),
        "beslut": "UNDERSÖK",
        "exact_identity_gate_supports_exact_comp_search": True,
        "exact_identity_gate_score": 90,
        "valuation_confidence_score": 60,
        "market_edge_score": 20,
        "sold_comparable_count": 1,
    }


def _listing():
    return {
        "titel": "Seller card",
        "lank": "https://example.test/item/1",
        "pris": 50,
        "seller": {
            "alias": "Etanol71",
            "id": 771,
            "url": "https://www.tradera.com/profile/items/771/Etanol71",
        },
    }


def test_quick_analysis_exposes_canonical_seller_metadata():
    out = quick_analyze_seller_inventory(
        {"tradera_item_id": "anchor"},
        [_listing()],
        analyze_fn=_fake_analyze,
        limit=5,
    )

    row = out["rows"][0]
    assert row["seller_alias"] == "Etanol71"
    assert row["seller_id"] == "771"
    assert row["seller_url"].endswith("/Etanol71")
    assert row["source_item"]["seller_alias"] == "Etanol71"


def test_full_analysis_exposes_canonical_seller_metadata():
    out = full_analyze_live_seller_item(
        _listing(),
        analyze_fn=_fake_analyze,
        all_items=[_listing()],
    )

    assert out["seller_alias"] == "Etanol71"
    assert out["seller_id"] == "771"
    assert out["seller_url"].endswith("/Etanol71")
    assert out["source_item"]["seller_alias"] == "Etanol71"
