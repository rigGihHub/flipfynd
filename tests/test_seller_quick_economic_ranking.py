from src.seller_live_quick_analysis import _economic_rank_key


def test_verified_profitable_card_beats_star_base_without_sales():
    profitable = {
        "identity_ok": True,
        "sold_comps": 2,
        "risk_adjusted_profit": 12,
        "deal_score": 35,
        "rank_score": 45,
        "player_market_score": 20,
        "decision": "KÖP",
    }
    star_base = {
        "identity_ok": False,
        "sold_comps": 0,
        "risk_adjusted_profit": 0,
        "deal_score": 5,
        "rank_score": 95,
        "player_market_score": 100,
        "collector_signal_score": 40,
        "decision": "UNDERSÖK",
    }
    assert _economic_rank_key(profitable) < _economic_rank_key(star_base)


def test_profit_with_sold_beats_same_profit_without_sold():
    verified = {"identity_ok": True, "sold_comps": 1, "risk_adjusted_profit": 10}
    unsupported = {"identity_ok": False, "sold_comps": 0, "risk_adjusted_profit": 10, "player_market_score": 100}
    assert _economic_rank_key(verified) < _economic_rank_key(unsupported)


def test_player_market_score_is_only_late_tiebreaker():
    low_star = {"identity_ok": True, "sold_comps": 2, "risk_adjusted_profit": 20, "player_market_score": 10}
    superstar = {"identity_ok": False, "sold_comps": 0, "risk_adjusted_profit": 0, "player_market_score": 100}
    assert _economic_rank_key(low_star) < _economic_rank_key(superstar)
