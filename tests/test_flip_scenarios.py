import unittest

from src.flip_scenarios import build_flip_scenarios


class FlipScenarioTests(unittest.TestCase):
    def test_uses_existing_values_without_creating_new_valuation(self):
        result = build_flip_scenarios(
            total_cost=100,
            floor_resale=150,
            expected_resale=200,
            best_case_resale=260,
            liquidity_score=70,
            sale_probability=65,
        )
        self.assertTrue(result["available"])
        self.assertEqual([s["resale_price"] for s in result["scenarios"]], [150.0, 200.0, 260.0])

    def test_quick_scenario_can_reveal_downside(self):
        result = build_flip_scenarios(
            total_cost=100,
            floor_resale=110,
            expected_resale=180,
            best_case_resale=240,
            liquidity_score=65,
            sale_probability=60,
        )
        quick = result["scenarios"][0]
        normal = result["scenarios"][1]
        self.assertLess(quick["net_profit"], 0)
        self.assertGreater(normal["net_profit"], 0)
        self.assertFalse(result["resilient_flip"])

    def test_quick_sale_is_more_liquid_than_best_case(self):
        result = build_flip_scenarios(
            total_cost=80,
            floor_resale=160,
            expected_resale=200,
            best_case_resale=250,
            liquidity_score=60,
            sale_probability=60,
        )
        quick, _, best = result["scenarios"]
        self.assertGreater(quick["sellability_score"], best["sellability_score"])

    def test_missing_economics_returns_unavailable(self):
        result = build_flip_scenarios(
            total_cost=0,
            floor_resale=0,
            expected_resale=0,
            best_case_resale=0,
            liquidity_score=50,
            sale_probability=50,
        )
        self.assertFalse(result["available"])


if __name__ == "__main__":
    unittest.main()
