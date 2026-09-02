import unittest

from src.card_intelligence import build_card_intelligence
from src.card_market_knowledge import detect_market_knowledge_signals


class CardIntelligenceTests(unittest.TestCase):
    def test_one_of_one_becomes_top_tier_without_price_claim(self):
        signals = [{
            "label": "Test 1/1",
            "category": "parallel",
            "print_run": 1,
            "attention_priority": 5,
            "source_id": "official_test",
        }]
        result = build_card_intelligence(signals, {})
        self.assertEqual(result["tier"], 5)
        self.assertIn("1/1", result["reasons"][0])
        self.assertNotIn("kr", result["summary"].lower())

    def test_future_watch_auto_patch_has_product_hierarchy(self):
        signals = detect_market_knowledge_signals(
            "2024-25 SP Authentic Future Watch Auto Patch Macklin Celebrini /100",
            sport="hockey",
        )
        result = build_card_intelligence(signals, {"rookie": True, "autograph": True, "patch": True})
        self.assertTrue(any("SP Authentic" in path for path in result["paths"]))
        self.assertGreaterEqual(result["tier"], 4)
        self.assertTrue(result["verification_steps"])

    def test_artifacts_black_rookie_auto_is_recognized(self):
        signals = detect_market_knowledge_signals(
            "2024-25 Artifacts Black Rookie Auto /5 Frank Nazar",
            sport="hockey",
        )
        labels = {s.get("label") for s in signals}
        self.assertIn("Artifacts Rookie Black Auto /5", labels)

    def test_sport_filter_prevents_cross_sport_signal(self):
        signals = detect_market_knowledge_signals(
            "Prizm Genesis football card",
            sport="hockey",
        )
        self.assertFalse(any(s.get("label") == "Prizm Genesis" for s in signals))

    def test_no_signal_stays_neutral(self):
        result = build_card_intelligence([], {})
        self.assertEqual(result["tier"], 0)
        self.assertEqual(result["paths"], [])


if __name__ == "__main__":
    unittest.main()
