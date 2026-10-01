import pytest

from src import seller_top5 as top


def item(i):
    return {"tradera_item_id": str(i), "lank": f"https://example.test/{i}",
            "titel": f"2023-24 Upper Deck Exclusive #{i} Player {i} /100", "pris": 20}


def quick_row(source):
    return {"source_item": source, "url": source["lank"], "title": source["titel"],
            "price": 20, "rank_score": 50, "quick_score": 60,
            "decision": "UNDERSÖK", "collector_signal_score": 20}


def analyze(source, **kwargs):
    return {"titel": source["titel"], "pris": 20, "lank": source["lank"],
            "beslut": "UNDERSÖK", "rank_score": int(source["tradera_item_id"]),
            "exact_identity_gate_supports_exact_comp_search": True,
            "exact_identity_gate_score": 90, "valuation_confidence_score": 60}


@pytest.mark.parametrize("asking_includes_new", [True, False])
def test_new_inventory_is_deep_analysed_ahead_of_old_asking_candidates(monkeypatch, asking_includes_new):
    inventory = [item(i) for i in range(1100)]
    old = [quick_row(source) for source in inventory[:24]]
    new = [quick_row(source) for source in inventory[1000:1010]]
    batches = iter([old, old + new])
    monkeypatch.setattr(top, "_quick_scan_inventory", lambda *a, **k: {"rows": next(batches)})
    # Simulate the asking route's bounded selection, with incumbents first.
    monkeypatch.setattr("src.asking_price_opportunity.select_asking_price_research",
                        lambda rows, limit=24: (rows if asking_includes_new else
                                               [row for row in rows if int(row["source_item"]["tradera_item_id"]) < 24])[:limit])
    first = top.build_seller_top5("seller", inventory, analyze_fn=analyze)
    second = top.build_seller_top5("seller", inventory, analyze_fn=analyze,
                                   analysis_registry=first["analysis_registry"])
    assert first["full_unique_analysed"] == 24
    assert second["full_unique_analysed"] == 34
    assert second["new_full_analysed"] == 10
    assert {str(i) for i in range(1000, 1010)} <= {
        key for key, entry in second["analysis_registry"]["entries"].items() if entry["full_count"]
    }
    assert any(int(row["source_item"]["tradera_item_id"]) >= 1000 for row in second["rows"])


def test_unfinished_quick_candidates_survive_next_fast_batch(monkeypatch):
    inventory = [item(i) for i in range(40)]
    batches = iter([[quick_row(source) for source in inventory[:12]], []])
    monkeypatch.setattr(top, "_quick_scan_inventory", lambda *a, **k: {"rows": next(batches)})
    monkeypatch.setattr("src.asking_price_opportunity.select_asking_price_research",
                        lambda rows, limit=24: rows[:limit])
    first = top.build_seller_top5("seller", inventory, analyze_fn=analyze, full_limit=8)
    assert first["full_unique_analysed"] == 8
    second = top.build_seller_top5("seller", inventory, analyze_fn=analyze, full_limit=8,
                                   analysis_registry=first["analysis_registry"])
    assert second["full_unique_analysed"] == 12
    assert first["pending_deep_analysis"] == 4
    assert second["new_quick_analysed"] == 0
    assert second["new_full_analysed"] == 4
    assert second["pending_deep_analysis"] == 0
