from src.seller_top5 import _seller_opportunity_rank_key


def test_sold_backed_positive_economics_beats_asking_only_margin():
    sold_backed = {
        "decision": "UNDERSÖK", "identity_ok": True, "sold_comps": 2,
        "risk_adjusted_profit": 20, "deal_score": 35, "rank_score": 40,
        "valuation_confidence": 70, "risk_score": 20,
        "title": "Ordinary card",
    }
    asking_only = {
        "decision": "UNDERSÖK", "identity_ok": True, "sold_comps": 0,
        "risk_adjusted_profit": 0, "deal_score": 11, "rank_score": 90,
        "player_market_score": 100,
        "asking_price_opportunity": {"possible_find": True, "net_margin": 500},
        "title": "Superstar numbered card /99",
    }
    assert _seller_opportunity_rank_key(sold_backed) > _seller_opportunity_rank_key(asking_only)


def test_asking_only_candidate_still_beats_weak_filler():
    asking = {
        "decision": "SKIP", "sold_comps": 0, "risk_adjusted_profit": 0,
        "asking_price_opportunity": {"possible_find": True, "net_margin": 10},
        "title": "Possible card",
    }
    weak = {"decision": "SKIP", "sold_comps": 0, "risk_adjusted_profit": 0, "title": "Weak card"}
    assert _seller_opportunity_rank_key(asking) > _seller_opportunity_rank_key(weak)
