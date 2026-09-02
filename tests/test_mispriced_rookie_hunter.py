import unittest

from src.mispriced_rookie_hunter import build_mispriced_rookie_signal


class MispricedRookieHunterTests(unittest.TestCase):
    def base(self, **overrides):
        kwargs = dict(
            item={"titel": "Connor Bedard rookie card", "raw_text": "2023-24 Upper Deck Young Guns #451 Connor Bedard"},
            features={
                "is_rookie": True,
                "identity_enriched_fields": ["set_name", "card_number", "season"],
                "identity_confidence_score": 82,
                "identity_conflicts": [],
                "is_lot": False,
            },
            rookie_importance={
                "matched": True,
                "importance_score": 93,
                "program_rule": {"patterns": ("young guns",)},
            },
            listing_quality={"score": 52},
            hidden_find={"score": 62},
            player_market_score=100,
            valuation_confidence_score=30,
            sold_comparable_count=0,
            total_cost=80,
            expected_resale=150,
        )
        kwargs.update(overrides)
        return build_mispriced_rookie_signal(**kwargs)

    def test_underdescribed_program_becomes_candidate(self):
        result = self.base()
        self.assertTrue(result["candidate"])
        self.assertGreaterEqual(result["score"], 70)
        self.assertFalse(result["price_gap_supported"])
        self.assertFalse(result["safe_for_valuation"])

    def test_comp_supported_price_gap_requires_sold_and_confidence(self):
        result = self.base(valuation_confidence_score=78, sold_comparable_count=3)
        self.assertTrue(result["price_gap_supported"])
        self.assertIn("Prisgap", result["label"])

    def test_no_price_gap_when_only_one_sold_comp(self):
        result = self.base(valuation_confidence_score=90, sold_comparable_count=1)
        self.assertFalse(result["price_gap_supported"])

    def test_identity_conflict_caps_score_and_blocks_candidate(self):
        features = {
            "is_rookie": True,
            "identity_enriched_fields": ["card_number", "parallel", "season"],
            "identity_confidence_score": 70,
            "identity_conflicts": ["card_number: titel=451 / annonsinfo=452"],
            "is_lot": False,
        }
        result = self.base(features=features, valuation_confidence_score=90, sold_comparable_count=5)
        self.assertLessEqual(result["score"], 44)
        self.assertFalse(result["candidate"])

    def test_non_rookie_is_ignored(self):
        result = self.base(rookie_importance={"matched": False})
        self.assertFalse(result["matched"])
        self.assertFalse(result["candidate"])


if __name__ == "__main__":
    unittest.main()
