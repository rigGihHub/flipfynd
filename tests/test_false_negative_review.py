from src.false_negative_review import build_false_negative_review, classify_false_negative

def sold_non_buy(profit=150, purchase=200, decision="KANSKE", **extra):
    row={"status":"sålt","recommended_decision":decision,"actual_net_profit":profit,"purchase_price":purchase,"deal_score_at_capture":82,"sport":"hockey"}
    row.update(extra); return row

def test_strong_winner_is_false_negative():
    r=classify_false_negative(sold_non_buy(150,200))
    assert r["eligible"] is True and r["is_false_negative"] is True

def test_small_profit_is_not_false_negative():
    assert classify_false_negative(sold_non_buy(40,100))["is_false_negative"] is False

def test_low_roi_is_not_false_negative():
    assert classify_false_negative(sold_non_buy(120,1000))["is_false_negative"] is False

def test_buy_and_unsold_are_not_eligible():
    assert classify_false_negative(sold_non_buy(200,200,decision="KÖP"))["eligible"] is False
    assert classify_false_negative({"status":"köpt","recommended_decision":"KANSKE","actual_net_profit":200})["eligible"] is False

def test_pattern_gate_requires_five_non_buy_outcomes():
    assert build_false_negative_review([sold_non_buy()] * 4)["supports_pattern_review"] is False
    assert build_false_negative_review([sold_non_buy()] * 5)["supports_pattern_review"] is True

def test_safety_downgrade_segment_is_visible():
    review=build_false_negative_review([sold_non_buy(decision="KANSKE", decision_confidence_downgraded_at_capture=True) for _ in range(5)])
    seg=next(x for x in review["segments"] if x["key"]=="confidence_block")
    assert seg["enough_for_pattern"] is True
    assert seg["false_negative_rate_pct"] == 100.0
