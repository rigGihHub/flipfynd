from src.model_review_dashboard import build_model_review_dashboard


def sold(decision="KÖP", profit=100, purchase=100, **extra):
    row={"status":"sålt","recommended_decision":decision,"actual_net_profit":profit,"purchase_price":purchase}
    row.update(extra)
    return row


def test_ignores_open_rows():
    d=build_model_review_dashboard([{"status":"köpt","recommended_decision":"KÖP","actual_net_profit":-100}])
    assert d["sold_count"] == 0


def test_buy_quality_uses_false_positive_review():
    d=build_model_review_dashboard([sold("KÖP", -10)])
    assert d["false_positive_count"] == 1
    assert d["buy_without_false_positive_rate_pct"] == 0.0


def test_missed_winner_uses_false_negative_review():
    d=build_model_review_dashboard([sold("KANSKE", 150, 200)])
    assert d["false_negative_count"] == 1


def test_manual_review_requires_twenty_completed_outcomes():
    assert build_model_review_dashboard([sold()] * 19)["supports_manual_model_review"] is False
    assert build_model_review_dashboard([sold()] * 20)["supports_manual_model_review"] is True


def test_decision_summary_reports_real_profitability():
    d=build_model_review_dashboard([sold("KÖP",100),sold("KÖP",-20)])
    buy=next(x for x in d["decision_summary"] if x["decision"]=="KÖP")
    assert buy["profitable_rate_pct"] == 50.0
    assert buy["median_actual_net_profit"] == 40.0


def test_signal_can_show_both_false_positive_and_false_negative_evidence():
    rows=[]
    rows += [sold("KÖP", -10, information_edge_candidate_at_capture=True) for _ in range(5)]
    rows += [sold("KANSKE", 150, 200, information_edge_candidate_at_capture=True) for _ in range(5)]
    d=build_model_review_dashboard(rows)
    seg=next(x for x in d["signals"] if x["key"]=="information_edge")
    assert seg["false_positive_rate_pct"] == 100.0
    assert seg["false_negative_rate_pct"] == 100.0
    assert seg["reviewable"] is True
