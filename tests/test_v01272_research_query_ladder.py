from src.research_query_ladder import build_research_query_ladder
from src.auto_comp_research import research_one


def test_ladder_keeps_player_and_number_on_every_rung():
    ident={"player_name":"Wayne Gretzky","season":"1995-96","set_name":"Pinnacle","card_number":"101"}
    out=build_research_query_ladder(ident)
    assert out["ready"] is True
    assert len(out["queries"]) >= 2
    for row in out["queries"]:
        q=row["query"].lower()
        assert "wayne gretzky" in q
        assert "#101" in q


def test_ladder_can_drop_set_only_for_discovery():
    ident={"player_name":"Jamal Musiala","season":"2022-23","set_name":"Topps Match Attax UCL","card_number":"100","parallel":"Super-Stars"}
    out=build_research_query_ladder(ident)
    no_set=[x for x in out["queries"] if x["level"]=="NO_SET"]
    assert no_set
    assert "Topps Match Attax UCL" not in no_set[0]["query"]
    assert "Jamal Musiala" in no_set[0]["query"]
    assert "#100" in no_set[0]["query"]


def test_ladder_requires_player_and_number():
    assert build_research_query_ladder({"player_name":"Wayne Gretzky","season":"1995-96"})["ready"] is False


def test_auto_research_exposes_ladder_but_not_sold_evidence():
    item={
        "titel":"1995-96 Pinnacle #101 Wayne Gretzky",
        "exact_identity_gate_supports_comp_research": True,
        "exact_identity_gate_research_identity_fields": {
            "player_name":"Wayne Gretzky","season":"1995-96","set_name":"Pinnacle","card_number":"101"
        },
    }
    out=research_one(item, sold_records=[])
    assert out["query_ladder"]
    assert out["creates_sold_evidence"] is False
    assert out["creates_buy_decision"] is False
