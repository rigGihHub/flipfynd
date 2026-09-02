import unittest

from src.analyzer import compute_risk_model, compute_deal_score_100, compute_max_purchase_price


class RiskModelTests(unittest.TestCase):
    def test_strong_evidence_can_be_low_risk(self):
        details = [
            {"market_state": "sold", "total_price": 95, "age_days": 10},
            {"market_state": "sold", "total_price": 100, "age_days": 18},
            {"market_state": "sold", "total_price": 105, "age_days": 25},
            {"market_state": "sold", "total_price": 102, "age_days": 40},
        ]
        out = compute_risk_model(
            valuation_confidence_score=90,
            identity_confidence_score=95,
            liquidity_score=82,
            listing_quality_score=90,
            sold_comparable_count=4,
            comparable_details=details,
            player_match_confidence="high",
            risks=[],
            sale_type="Köp nu",
        )
        self.assertEqual(out["level"], "låg")
        self.assertLessEqual(out["score"], 30)
        self.assertGreaterEqual(out["max_bid_factor"], 0.95)

    def test_weak_evidence_is_high_risk(self):
        out = compute_risk_model(
            valuation_confidence_score=20,
            identity_confidence_score=35,
            liquidity_score=30,
            listing_quality_score=40,
            sold_comparable_count=0,
            asking_comparable_count=4,
            rejected_comparable_count=3,
            player_match_confidence="low",
            risks=["osäker parallel", "låg värderingssäkerhet"],
            is_lot=True,
            extreme_discount=True,
            sale_type="auktion",
        )
        self.assertEqual(out["level"], "hög")
        self.assertGreaterEqual(out["score"], 60)
        self.assertLessEqual(out["max_bid_factor"], 0.78)

    def test_price_dispersion_increases_risk(self):
        stable = [
            {"market_state": "sold", "total_price": 100},
            {"market_state": "sold", "total_price": 105},
            {"market_state": "sold", "total_price": 98},
        ]
        volatile = [
            {"market_state": "sold", "total_price": 40},
            {"market_state": "sold", "total_price": 100},
            {"market_state": "sold", "total_price": 220},
        ]
        kwargs = dict(
            valuation_confidence_score=75,
            identity_confidence_score=85,
            liquidity_score=70,
            listing_quality_score=80,
            sold_comparable_count=3,
            player_match_confidence="high",
            risks=[],
        )
        a = compute_risk_model(comparable_details=stable, **kwargs)
        b = compute_risk_model(comparable_details=volatile, **kwargs)
        self.assertGreater(b["score"], a["score"])

    def test_risk_score_reduces_deal_score(self):
        args = dict(
            profits={"net_profit_estimate": 120, "roi_estimate": 1.4},
            expected_resale=220,
            total_cost=80,
            probability=75,
            liquidity=75,
            valuation_confidence_score=80,
            identity_confidence_score=90,
            deal_confidence_score=85,
            risks=[],
            decision="KÖP",
        )
        low = compute_deal_score_100(risk_score=15, **args)
        high = compute_deal_score_100(risk_score=85, **args)
        self.assertLess(high["score"], low["score"])
        self.assertIn("risk_safety", high["components"])

    def test_high_risk_factor_reduces_max_purchase_ceiling(self):
        item = {"pris": 20, "frakt": 20, "sale_type": "Köp nu"}
        base = compute_max_purchase_price(
            item, 220, 160, 75, 80, 0.85, "high", risk_ceiling_factor=1.0
        )
        guarded = compute_max_purchase_price(
            item, 220, 160, 75, 80, 0.85, "high", risk_ceiling_factor=0.70
        )
        self.assertIsNotNone(base)
        self.assertIsNotNone(guarded)
        self.assertLess(guarded["max_total_price"], base["max_total_price"])


if __name__ == "__main__":
    unittest.main()
