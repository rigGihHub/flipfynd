import unittest

from src.collector_intelligence import build_collector_intelligence_matrix


class CollectorIntelligenceMatrixTests(unittest.TestCase):
    def test_elite_player_plus_premium_structure_is_high_priority(self):
        result = build_collector_intelligence_matrix(
            player_name="Connor Bedard",
            player_market_score=100,
            demand_tier="elite",
            card_intelligence={"tier": 5, "level": "Mycket viktig kortstruktur"},
            features={"rookie": True, "card_number": "451", "serial_denominator": 25},
        )
        self.assertGreaterEqual(result["score"], 88)
        self.assertEqual(result["level"], "A-kombination")
        self.assertFalse(result["safe_for_valuation"])

    def test_premium_structure_does_not_rescue_weak_player(self):
        result = build_collector_intelligence_matrix(
            player_name="Example Player",
            player_market_score=40,
            demand_tier="low",
            card_intelligence={"tier": 5, "level": "Mycket viktig kortstruktur"},
            features={"card_number": "10"},
        )
        self.assertLessEqual(result["score"], 62)
        self.assertTrue(any("svag spelarefterfrågan" in x.lower() for x in result["cautions"]))

    def test_unknown_player_is_capped(self):
        result = build_collector_intelligence_matrix(
            player_name=None,
            player_market_score=0,
            demand_tier=None,
            card_intelligence={"tier": 5, "level": "Mycket viktig kortstruktur"},
            features={"card_number": "7"},
        )
        self.assertLessEqual(result["score"], 48)

    def test_elite_player_base_card_is_player_driven_not_premium(self):
        result = build_collector_intelligence_matrix(
            player_name="Lamine Yamal",
            player_market_score=100,
            demand_tier="elite",
            card_intelligence={"tier": 1, "level": "Grundsignal"},
            features={},
        )
        self.assertIn("Spelardrivet", result["archetype"])
        self.assertLess(result["score"], 80)

    def test_matrix_never_claims_price(self):
        result = build_collector_intelligence_matrix(
            player_name="Connor McDavid",
            player_market_score=96,
            demand_tier="elite",
            card_intelligence={"tier": 4, "level": "Viktig kortstruktur"},
            features={"autograph": True, "card_number": "97"},
        )
        text = " ".join(result["reasons"] + [result["note"], result["next_action"]]).lower()
        self.assertNotIn(" kr", text)
        self.assertFalse(result["safe_for_valuation"])


if __name__ == "__main__":
    unittest.main()
