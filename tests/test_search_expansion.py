from src.search_expansion import (
    build_query_variants,
    build_search_matrix,
    build_search_expansion_plan,
    tradera_api_readiness,
)


def test_no_player_means_no_queries():
    assert build_query_variants({}) == []


def test_variants_only_reuse_structured_player_and_fields():
    rows=build_query_variants({
        "player_name":"Connor McDavid",
        "set_name":"Upper Deck",
        "season":"2015-16",
    })
    queries=[r["query"] for r in rows]
    assert "Connor McDavid" in queries
    assert "McDavid" in queries
    assert "Connor McDavid Upper Deck" in queries
    assert "Connor McDavid Upper Deck 2015-16" in queries


def test_rookie_query_requires_existing_rookie_signal():
    base={"player_name":"Connor McDavid"}
    assert all("rookie" not in r["query"].casefold() for r in build_query_variants(base))
    rows=build_query_variants({**base,"rookie_importance_matched":True})
    assert any("rookie" in r["query"].casefold() for r in rows)


def test_matrix_uses_known_category_and_multiple_orderings():
    matrix=build_search_matrix({"player_name":"X Yyyy"},"Hockey - NHL")
    assert matrix
    assert {r["category_id"] for r in matrix}=={293316}
    assert {"Relevance","PriceAscending","EndDateAscending"}.issubset({r["order_by"] for r in matrix})


def test_low_confidence_players_are_excluded_from_plan():
    plan=build_search_expansion_plan([
        {"player_name":"Wrong Guess","player_match_confidence":"low","player_market_score":99},
        {"player_name":"Safe Player","player_match_confidence":"high","player_market_score":80},
    ],"Fotboll")
    assert plan["players_used"]==["Safe Player"]
    assert plan["creates_identity"] is False
    assert plan["creates_value"] is False
    assert plan["creates_buy_decision"] is False


def test_api_readiness_fails_closed_without_credentials():
    out=tradera_api_readiness({})
    assert out["ready"] is False


def test_api_readiness_accepts_nonplaceholder_credentials():
    out=tradera_api_readiness({"TRADERA_APP_ID":"123","TRADERA_APP_KEY":"secret"})
    assert out["ready"] is True
