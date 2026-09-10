from src.tradera_api_search import normalize_search_item

def test_candidate_preserves_query_kind():
    out=normalize_search_item({"itemId":1,"title":"Card","price":10},category_name="Hockey - NHL",query="McDavid",order_by="PriceAscending",query_kind="player-exact")
    assert out["search_expansion_kind"]=="player-exact"
