from src.price_route_coverage import add_price_route_coverage


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
