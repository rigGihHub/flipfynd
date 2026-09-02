import unittest
from src.analyzer import compute_liquidity_evidence

class LiquidityEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.profile = {"score": 75}

    def test_recent_sold_comps_raise_liquidity(self):
        details = [
            {"market_state": "sold", "age_days": 5},
            {"market_state": "sold", "age_days": 12},
            {"market_state": "sold", "age_days": 25},
            {"market_state": "sold", "age_days": 60},
        ]
        out = compute_liquidity_evidence(55, self.profile, 100, details, 4, 0)
        self.assertEqual(out["evidence"], "sold")
        self.assertEqual(out["sold_30d"], 3)
        self.assertGreater(out["score"], 60)

    def test_asking_only_cannot_prove_high_liquidity(self):
        out = compute_liquidity_evidence(90, self.profile, 100, [], 0, 10)
        self.assertEqual(out["evidence"], "asking_only")
        self.assertLessEqual(out["score"], 68)

    def test_no_market_data_is_explicitly_heuristic(self):
        out = compute_liquidity_evidence(80, self.profile, 100, [], 0, 0)
        self.assertEqual(out["evidence"], "heuristic")
        self.assertLessEqual(out["score"], 72)
        self.assertTrue(any("heuristisk" in r for r in out["reasons"]))

    def test_weak_player_without_sales_is_capped(self):
        out = compute_liquidity_evidence(75, {"score": 25}, 50, [], 0, 0)
        self.assertLessEqual(out["score"], 55)

if __name__ == '__main__':
    unittest.main()
