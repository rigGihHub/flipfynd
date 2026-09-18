from src.seller_top5 import _fallback_row, _card_opportunity_key


def test_weak_fallback_is_not_labeled_as_a_find():
    row = _fallback_row({
        "title": "Ordinary card", "price": 10, "decision": "SKIP",
        "source_item": {"title": "Ordinary card", "id": "1"},
    }, "seller")
    assert "BÄST AV RESTEN" in row["label"]
    assert "KÖP" not in row["label"]


def test_distinct_listing_fallbacks_remain_distinct():
    a = _fallback_row({"title": "Card A", "source_item": {"title": "Card A", "id": "1"}}, "seller")
    b = _fallback_row({"title": "Card B", "source_item": {"title": "Card B", "id": "2"}}, "seller")
    assert _card_opportunity_key(a) != _card_opportunity_key(b)
