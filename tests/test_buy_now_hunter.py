from src.buy_now_hunter import build_buy_now_opportunity


def base(**overrides):
    row = {
        "sale_type": "Köp nu",
        "total_cost": 500,
        "expected_resale": 900,
        "net_profit_estimate": 250,
        "roi_estimate": 0.50,
        "valuation_confidence_score": 82,
        "exact_identity_gate_score": 88,
        "exact_identity_gate_supports_exact_comp_search": True,
        "risk_score": 20,
        "sold_comparable_count": 4,
        "detail_evidence_fusion_has_conflict": False,
        "identity_conflicts": [],
        "is_lot": False,
    }
    row.update(overrides)
    return row


def test_strong_buy_now_is_eligible():
    out = build_buy_now_opportunity(base())
    assert out["eligible"] is True
    assert out["score"] >= 65
    assert out["safe_for_valuation"] is False


def test_auction_is_not_eligible():
    out = build_buy_now_opportunity(base(sale_type="Auktion"))
    assert out["eligible"] is False
    assert out["score"] == 0


def test_weak_evidence_blocks():
    out = build_buy_now_opportunity(base(sold_comparable_count=1, valuation_confidence_score=45))
    assert out["eligible"] is False
    assert out["score"] == 0
    assert len(out["blockers"]) >= 2


def test_identity_conflict_blocks():
    out = build_buy_now_opportunity(base(identity_conflicts=["serial mismatch"]))
    assert out["eligible"] is False


def test_no_value_fields_are_created():
    out = build_buy_now_opportunity(base())
    for key in ("market_value", "expected_resale", "max_bid", "max_purchase_price", "profit"):
        assert key not in out
