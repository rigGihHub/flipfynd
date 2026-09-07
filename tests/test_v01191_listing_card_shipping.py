from src.novice_navigation import build_best_available_view, build_watch_view

def test_best_available_exposes_known_shipping():
    row={"titel":"Kort A","beslut":"SKIP","frakt":19,"total_cost":119,"deal_score":10}
    out=build_best_available_view([row])
    assert out["rows"][0]["shipping"] == 19
    assert out["rows"][0]["shipping_known"] is True

def test_best_available_marks_shipping_assumption():
    row={"titel":"Kort B","beslut":"SKIP","total_cost":129,"deal_score":10}
    out=build_best_available_view([row])
    assert out["rows"][0]["shipping"] == 29
    assert out["rows"][0]["shipping_known"] is False

def test_watch_exposes_shipping():
    row={"titel":"Kort C","beslut":"KANSKE","frakt":25,"analysis_total_cost":125}
    out=build_watch_view([row])
    assert out["rows"][0]["shipping"] == 25
    assert out["rows"][0]["shipping_known"] is True
