import unittest

from src.dynamic_max_bid import build_dynamic_max_bid


class DynamicMaxBidTests(unittest.TestCase):
    def test_never_creates_bid_without_base_ceiling(self):
        result = build_dynamic_max_bid(
            base_max_total=None,
            shipping=29,
            comp_verdict={"supports_safe_max_bid": True, "score": 95, "exact_count": 6},
        )
        self.assertFalse(result["available"])
        self.assertIsNone(result["max_total_price"])

    def test_weak_comp_verdict_does_not_issue_dynamic_bid(self):
        result = build_dynamic_max_bid(
            base_max_total=500,
            shipping=29,
            comp_verdict={"supports_safe_max_bid": False, "score": 55, "exact_count": 2},
        )
        self.assertFalse(result["available"])
        self.assertIsNone(result["max_total_price"])

    def test_strong_evidence_can_only_tighten_base_bid(self):
        result = build_dynamic_max_bid(
            base_max_total=500,
            shipping=29,
            comp_verdict={
                "supports_safe_max_bid": True,
                "score": 90,
                "exact_count": 5,
                "recent_exact_count": 4,
                "relative_spread": 0.12,
                "price_median": 700,
            },
        )
        self.assertTrue(result["available"])
        self.assertLessEqual(result["max_total_price"], 500)
        self.assertEqual(result["max_total_price"], 490.0)
        self.assertEqual(result["max_item_price"], 461.0)

    def test_comp_median_can_be_stricter_than_base_factor(self):
        result = build_dynamic_max_bid(
            base_max_total=800,
            shipping=30,
            comp_verdict={
                "supports_safe_max_bid": True,
                "score": 82,
                "exact_count": 4,
                "recent_exact_count": 2,
                "relative_spread": 0.25,
                "price_median": 700,
            },
        )
        self.assertTrue(result["available"])
        self.assertEqual(result["comp_price_cap"], 560.0)
        self.assertEqual(result["max_total_price"], 560.0)
        self.assertEqual(result["max_item_price"], 530.0)

    def test_safe_minimum_never_drops_below_shipping(self):
        result = build_dynamic_max_bid(
            base_max_total=35,
            shipping=29,
            comp_verdict={
                "supports_safe_max_bid": True,
                "score": 75,
                "exact_count": 3,
                "recent_exact_count": 1,
                "relative_spread": 0.35,
                "price_median": 20,
            },
        )
        self.assertEqual(result["max_total_price"], 29.0)
        self.assertEqual(result["max_item_price"], 0.0)


if __name__ == "__main__":
    unittest.main()
