import unittest
from datetime import datetime, timezone

from src.comp_verdict import build_comp_verdict


class CompVerdictTests(unittest.TestCase):
    def hunt(self, prices, near=0, rejected=0):
        return {
            "unlocked": True,
            "exact": [{"price": p, "sold_at": "2026-08-01"} for p in prices],
            "near": [{} for _ in range(near)],
            "rejected": [{} for _ in range(rejected)],
        }

    def test_locked_stays_without_verdict(self):
        result = build_comp_verdict({"unlocked": False})
        self.assertEqual(result["score"], 0)
        self.assertFalse(result["supports_safe_max_bid"])

    def test_one_exact_is_not_safe(self):
        result = build_comp_verdict(self.hunt([900]), now=datetime(2026, 9, 1, tzinfo=timezone.utc))
        self.assertIn("För få", result["verdict"])
        self.assertFalse(result["supports_safe_max_bid"])

    def test_three_tight_exact_sales_support_cautious_ceiling(self):
        result = build_comp_verdict(self.hunt([890, 900, 910]), now=datetime(2026, 9, 1, tzinfo=timezone.utc))
        self.assertGreaterEqual(result["score"], 70)
        self.assertTrue(result["supports_safe_max_bid"])
        self.assertEqual(result["price_median"], 900)

    def test_spread_blocks_safe_ceiling(self):
        result = build_comp_verdict(self.hunt([400, 900, 1600]), now=datetime(2026, 9, 1, tzinfo=timezone.utc))
        self.assertIn("spretig", result["verdict"])
        self.assertFalse(result["supports_safe_max_bid"])

    def test_rejected_records_reduce_score(self):
        clean = build_comp_verdict(self.hunt([890, 900, 910]), now=datetime(2026, 9, 1, tzinfo=timezone.utc))
        dirty = build_comp_verdict(self.hunt([890, 900, 910], rejected=4), now=datetime(2026, 9, 1, tzinfo=timezone.utc))
        self.assertLess(dirty["score"], clean["score"])


if __name__ == "__main__":
    unittest.main()
