from src.market_analysis import _normalize_features, _normalize_title_features


def test_market_title_features_are_parsed_once_and_returned_as_copies():
    _normalize_title_features.cache_clear()
    item = {"titel": "2023-24 Upper Deck Connor McDavid #97"}

    first = _normalize_features(item)
    second = _normalize_features(item)

    cache = _normalize_title_features.cache_info()
    assert cache.misses == 1
    assert cache.hits == 1
    assert first == second
    assert first is not second

    first["player_name"] = "Ändrad"
    assert _normalize_features(item).get("player_name") != "Ändrad"
