from src.tradera_fetcher import (
    CATEGORY_IDS,
    MAX_ACTIVE_ITEMS_PER_CATEGORY,
    SMART_MAX_PAGES,
    SMART_STOP_AFTER_KNOWN_PAGES,
    infer_category_from_item_url,
    prune_active_items,
)


def test_category_ids_are_explicit_and_separate():
    assert CATEGORY_IDS["293316"] == "Hockey - NHL"
    assert CATEGORY_IDS["293311"] == "Fotboll"


def test_item_url_overrides_wrong_source_category():
    assert infer_category_from_item_url(
        "https://www.tradera.com/item/293316/748227274/example",
        "Fotboll",
    ) == "Hockey - NHL"


def test_unknown_item_url_keeps_fallback():
    assert infer_category_from_item_url(
        "https://www.tradera.com/item/999999/123/example",
        "Fotboll",
    ) == "Fotboll"


def test_prune_bounds_each_sport_and_repairs_category():
    rows = []
    for idx in range(8):
        rows.append({
            "lank": f"https://www.tradera.com/item/293316/{1000+idx}/hockey",
            "source_category": "Fotboll",  # deliberately wrong legacy label
            "sida": idx + 1,
        })
    for idx in range(9):
        rows.append({
            "lank": f"https://www.tradera.com/item/293311/{2000+idx}/football",
            "source_category": "Hockey - NHL",  # deliberately wrong legacy label
            "sida": idx + 1,
        })

    pruned = prune_active_items(rows, max_per_category=5)
    hockey = [x for x in pruned if x["source_category"] == "Hockey - NHL"]
    football = [x for x in pruned if x["source_category"] == "Fotboll"]

    assert len(hockey) == 5
    assert len(football) == 5
    assert max(x["sida"] for x in hockey) == 5
    assert max(x["sida"] for x in football) == 5


def test_cloud_safe_defaults_are_bounded():
    assert SMART_MAX_PAGES <= 12
    assert SMART_STOP_AFTER_KNOWN_PAGES <= 2
    assert MAX_ACTIVE_ITEMS_PER_CATEGORY <= 1500
