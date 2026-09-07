from src.error_segmentation import build_error_segmentation

def row(**kw):
    base = {
        "status":"sålt","actual_net_profit":80,"expected_net_profit_at_capture":100,
        "actual_roi_pct":40,"expected_roi_pct_at_capture":50,
        "days_to_sell":15,"flip_velocity_days_at_capture":10,
        "sport":"Hockey","purchase_price":200,"risk_score_at_capture":30,
        "sellability_at_capture":80,"valuation_confidence_at_capture":80,
        "exact_comp_available_at_capture":True,
        "mispriced_rookie_candidate_at_capture":False,
        "market_edge_candidate_at_capture":False,
        "information_edge_candidate_at_capture":False,
    }
    base.update(kw)
    return base

def test_open_rows_ignored():
    r = build_error_segmentation([row(status="köpt")])
    assert r["sold_count"] == 0

def test_sport_segment_created():
    r = build_error_segmentation([row()])
    assert any(x["segment"]=="sport" and x["label"]=="Hockey" for x in r["segments"])

def test_price_band():
    r = build_error_segmentation([row(purchase_price=90)])
    assert any(x["segment"]=="price_band" and x["label"]=="<100 kr" for x in r["segments"])

def test_five_rows_make_segment_reviewable():
    r = build_error_segmentation([row() for _ in range(5)])
    assert any(x["segment"]=="sport" and x["enough"] for x in r["reviewable"])

def test_missing_prediction_does_not_create_fake_error():
    rows=[row(expected_net_profit_at_capture=None) for _ in range(5)]
    r=build_error_segmentation(rows)
    sport=next(x for x in r["segments"] if x["segment"]=="sport")
    assert sport["profit"]["count"]==0

def test_exact_comp_split():
    rows=[row(exact_comp_available_at_capture=True), row(exact_comp_available_at_capture=False)]
    r=build_error_segmentation(rows)
    labels={x["label"] for x in r["segments"] if x["segment"]=="exact_comp"}
    assert labels=={"Exakt comp fanns","Ingen exakt comp"}


def test_cross_unit_errors_are_never_combined_into_severity():
    rows=[row() for _ in range(5)]
    r=build_error_segmentation(rows)
    assert "reviewable_by_metric" in r
    assert set(r["reviewable_by_metric"])=={"profit","roi","velocity"}
    assert all("severity" not in s for s in r["reviewable"])

def test_profit_ranking_uses_profit_error_only():
    rows=[row(sport="Hockey",actual_net_profit=0,expected_net_profit_at_capture=100,days_to_sell=11,flip_velocity_days_at_capture=10) for _ in range(5)]
    rows += [row(sport="Football",actual_net_profit=90,expected_net_profit_at_capture=100,days_to_sell=100,flip_velocity_days_at_capture=10) for _ in range(5)]
    r=build_error_segmentation(rows)
    profit=r["reviewable_by_metric"]["profit"]
    assert next(x for x in profit if x["segment"]=="sport")["label"]=="Hockey"
