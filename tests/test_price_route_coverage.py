from src.price_route_coverage import add_price_route_coverage, spread_price_routes
from src.asking_price_opportunity import asking_research_identity, select_asking_price_research


def test_adds_exact_routes_without_expanding_budget_or_replacing_protected_lane():
    selected = [{"id": str(i)} for i in range(8)]
    routes = [selected[2], {"id": "new-a"}, {"id": "new-b"}]
    result, added = add_price_route_coverage(selected, routes, max_new=2)
    assert added == 2
    assert len(result) == len(selected)
    assert result[:2] == selected[:2]
    assert {row["id"] for row in result} == {"0", "1", "2", "3", "4", "5", "new-a", "new-b"}


def test_no_routes_or_replacement_space_does_not_displace_anything():
    selected = [{"id": str(i)} for i in range(4)]
    result, added = add_price_route_coverage(selected, selected + [{"id": "new"}], max_new=2)
    assert (result, added) == (selected, 0)


def test_price_routes_probe_beyond_cheapest_cluster():
    routes = [{"id": str(index)} for index in range(100)]
    selected = spread_price_routes(routes, limit=10)
    assert len(selected) == 10
    assert selected[:6] == routes[:6]
    assert int(selected[-1]["id"]) >= 70


def test_raw_title_can_route_research_before_full_analysis(monkeypatch):
    monkeypatch.setattr("src.asking_price_opportunity.configured_credentials", lambda: ("id", "secret"))
    raw = {
        "titel": "2022/23 Topps UCL Super-Stars #100 Jamal Musiala Uncommon Green Pris: 35 kr",
        "pris": 35, "frakt": 22, "id": "outside-fast-pool",
    }
    identity = asking_research_identity(raw)
    assert identity["player_name"] == "Jamal Musiala"
    assert identity["set_name"] == "Topps UCL Super-Stars"
    assert identity["season"] == "2022-23"
    assert identity["card_number"] == "100"
    assert select_asking_price_research([{"source_item": raw}], limit=1)[0]["source_item"] is raw
