from src.seller_profit_display import build_seller_net_profit_summary, known_negative_net_profit


def test_active_price_scenario_shows_negative_net_profit():
    result = build_seller_net_profit_summary({
        "risk_adjusted_profit": 80,
        "asking_price_opportunity": {"net_margin": -17},
    })
    assert result["available"] is True
    assert result["value"] == -17
    assert result["label"] == "Nettovinst mot prisindikation"


def test_verified_net_profit_is_shown_after_costs():
    result = build_seller_net_profit_summary({
        "net_profit_estimate": 42,
        "valuation_display_safe": True,
    })
    assert result["available"] is True
    assert result["value"] == 42


def test_ordinary_top5_keeps_negative_active_price_net_profit_visible():
    result = build_seller_net_profit_summary({"asking_net_margin": -24})
    assert result["available"] is True
    assert result["value"] == -24


def test_risk_adjusted_profit_alone_never_becomes_net_profit():
    result = build_seller_net_profit_summary({"risk_adjusted_profit": 999})
    assert result["available"] is False
    assert result["value"] is None


def test_unsafe_valuation_is_explicitly_unavailable():
    result = build_seller_net_profit_summary({
        "net_profit_estimate": 42,
        "valuation_display_safe": False,
    })
    assert result["available"] is False
    assert "ej beräkningsbar" in result["basis"]


def test_known_negative_profit_is_not_a_recommendation():
    assert known_negative_net_profit({"asking_net_margin": -1}) is True
    assert known_negative_net_profit({"asking_net_margin": 0}) is False
