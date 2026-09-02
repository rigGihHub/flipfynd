import unittest

from src.player_card_demand import build_player_card_demand


class PlayerCardDemandTests(unittest.TestCase):
    def test_elite_player_and_strong_structure_is_high(self):
        result = build_player_card_demand(
            player_name="Elite Player", player_market_score=96, demand_tier="elite",
            variant_rung=4, rookie_rung=4, chase_priority_score=80,
            sold_comparable_count=4, asking_comparable_count=2, liquidity_score=82,
            sold_30d=2, sold_90d=4, identity_confidence_score=90,
            valuation_confidence_score=82,
        )
        self.assertGreaterEqual(result["score"], 80)
        self.assertGreaterEqual(result["review_priority_score"], 70)
        self.assertGreater(result["preselection_boost"], 0)
        self.assertFalse(result["safe_for_valuation"])

    def test_rare_card_weak_player_is_capped(self):
        result = build_player_card_demand(
            player_name="Weak Player", player_market_score=35, demand_tier="low",
            variant_rung=6, rookie_rung=0, chase_priority_score=95,
            sold_comparable_count=0, asking_comparable_count=5, liquidity_score=60,
            identity_confidence_score=90, valuation_confidence_score=50,
        )
        self.assertLessEqual(result["score"], 68)
        self.assertTrue(any("Sällsynt struktur" in x for x in result["cautions"]))

    def test_no_sold_comps_is_uncertainty_not_zero_demand(self):
        result = build_player_card_demand(
            player_name="Known Player", player_market_score=90, demand_tier="high",
            variant_rung=2, rookie_rung=2, chase_priority_score=40,
            sold_comparable_count=0, asking_comparable_count=0, liquidity_score=70,
            identity_confidence_score=80, valuation_confidence_score=20,
        )
        self.assertEqual(result["market_component"], 50)
        self.assertGreater(result["score"], 50)
        self.assertLess(result["confidence_score"], 60)

    def test_unknown_player_cannot_look_elite(self):
        result = build_player_card_demand(
            player_name=None, player_market_score=0, demand_tier=None,
            variant_rung=6, rookie_rung=5, chase_priority_score=100,
            sold_comparable_count=6, asking_comparable_count=0, liquidity_score=90,
            sold_30d=4, sold_90d=6, identity_confidence_score=90,
            valuation_confidence_score=90,
        )
        self.assertLessEqual(result["score"], 55)

    def test_low_identity_caps_demand(self):
        result = build_player_card_demand(
            player_name="Elite Player", player_market_score=98, demand_tier="elite",
            variant_rung=5, rookie_rung=4, chase_priority_score=90,
            sold_comparable_count=4, asking_comparable_count=0, liquidity_score=90,
            sold_30d=2, sold_90d=4, identity_confidence_score=30,
            valuation_confidence_score=85,
        )
        self.assertLessEqual(result["score"], 64)


if __name__ == "__main__":
    unittest.main()
