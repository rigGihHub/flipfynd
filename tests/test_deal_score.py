import unittest
from src.analyzer import compute_deal_score_100

class DealScoreTests(unittest.TestCase):
    def score(self, **overrides):
        args=dict(
            profits={"net_profit_estimate":120,"roi_estimate":1.5}, expected_resale=220,
            total_cost=80, probability=78, liquidity=80, valuation_confidence_score=85,
            identity_confidence_score=90, deal_confidence_score=88, risks=[], decision="KÖP")
        args.update(overrides)
        return compute_deal_score_100(**args)

    def test_good_flip_scores_high(self):
        self.assertGreaterEqual(self.score()["score"], 70)
    def test_weak_valuation_caps_score(self):
        self.assertLessEqual(self.score(valuation_confidence_score=20)["score"], 64)
    def test_skip_cannot_be_high_score(self):
        self.assertLessEqual(self.score(decision="SKIP")["score"], 49)
    def test_negative_profit_cannot_be_good_find(self):
        r=self.score(profits={"net_profit_estimate":-10,"roi_estimate":-0.1})
        self.assertLessEqual(r["score"],45)
    def test_score_exposes_components(self):
        self.assertIn("roi", self.score()["components"])

if __name__ == '__main__': unittest.main()
