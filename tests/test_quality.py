import json
import unittest
from pathlib import Path

from src.analyzer import analyze_item, collectible_demand_factor, compute_comp_weight, compute_entry_cost, detect_sale_type, estimate_title_value, get_features, grading_trait_bonus, make_decision, premium_trait_bonus, rookie_trait_bonus
from src.player_market import load_player_market, match_player, normalize_player_name
from src.pricing import DEFAULT_UNKNOWN_SHIPPING, normalize_shipping, total_acquisition_cost
from src.market_analysis import _safe_total_cost


class PricingTests(unittest.TestCase):
    def test_unknown_shipping_is_conservative(self):
        self.assertEqual(normalize_shipping(None), DEFAULT_UNKNOWN_SHIPPING)
        self.assertEqual(total_acquisition_cost(100, None), 100 + DEFAULT_UNKNOWN_SHIPPING)

    def test_known_shipping_is_preserved(self):
        self.assertEqual(total_acquisition_cost(100, 19), 119)
        self.assertEqual(total_acquisition_cost(100, 0), 100)

    def test_invalid_price_is_rejected(self):
        self.assertIsNone(total_acquisition_cost(None, 29))
        self.assertIsNone(total_acquisition_cost(0, 29))


class PlayerMarketTests(unittest.TestCase):
    def test_alias_normalization(self):
        self.assertEqual(normalize_player_name("Kylian Mbappe"), "Kylian Mbappé")

    def test_typo_tolerance_is_not_high_confidence(self):
        match = match_player("2023 Connor Bedard Young Guns rookie", "hockey")
        self.assertEqual(match["name"], "Connor Bedard")
        self.assertEqual(match["confidence"], "high")

        fuzzy = match_player("2023 Conor Bedard Young Guns rookie", "hockey")
        self.assertEqual(fuzzy["name"], "Connor Bedard")
        self.assertEqual(fuzzy["confidence"], "medium")

    def test_cross_sport_player_not_matched(self):
        self.assertIsNone(match_player("Connor Bedard rookie card", "football")["name"])

    def test_player_data_integrity(self):
        data = load_player_market()
        canonical = set(data.get("hockey", {})) | set(data.get("football", {}))
        self.assertFalse(set(data.get("hockey", {})) & set(data.get("football", {})))
        for sport in ("hockey", "football"):
            for name, info in data.get(sport, {}).items():
                self.assertTrue(name.strip())
                self.assertIsInstance(info.get("score"), int)
                self.assertGreaterEqual(info["score"], 0)
                self.assertLessEqual(info["score"], 100)
                self.assertIn(info.get("tier"), {"weak", "medium", "strong", "elite"})
        for alias, target in data.get("aliases", {}).items():
            self.assertTrue(alias.strip())
            self.assertIn(target, canonical)


class MarketAnalysisConsistencyTests(unittest.TestCase):
    def test_comp_analysis_uses_conservative_unknown_shipping(self):
        self.assertEqual(
            _safe_total_cost({"pris": 100, "frakt": None}),
            100 + DEFAULT_UNKNOWN_SHIPPING,
        )

    def test_active_listing_comp_weights_are_conservative(self):
        self.assertEqual(compute_comp_weight(1, "hög"), 0.0)
        self.assertEqual(compute_comp_weight(2, "låg"), 0.15)
        self.assertEqual(compute_comp_weight(5, "låg"), 0.20)
        self.assertEqual(compute_comp_weight(2, "medel"), 0.30)
        self.assertEqual(compute_comp_weight(5, "hög"), 0.50)


class AnalysisConsistencyTests(unittest.TestCase):
    def test_analysis_uses_same_unknown_shipping_rule(self):
        item = {
            "titel": "Connor Bedard Young Guns rookie",
            "pris": 100,
            "frakt": None,
            "source_category": "hockey",
            "lank": "https://example.invalid/item",
        }
        result = analyze_item(item, sport="hockey", strategy_mode="quick_flip", mode="fast")
        self.assertEqual(result["total_cost"], 100 + DEFAULT_UNKNOWN_SHIPPING)

    def test_unknown_player_stays_low_confidence(self):
        features = get_features("Mystery Person rare card", "hockey")
        self.assertEqual(features["player_match_confidence"], "low")



class DecisionGuardrailTests(unittest.TestCase):
    def test_strong_buy_requires_capital_efficiency(self):
        decision = make_decision(
            net_profit=100, risk_adjusted=70, probability=70, player_score=90,
            confidence=0.75, player_match_confidence="high", floor_profit=-20,
            roi=0.10, total_cost=1000,
        )
        self.assertNotIn(decision, {"KÖP", "KÖP (starkt fynd)"})

    def test_large_downside_blocks_clear_buy(self):
        decision = make_decision(
            net_profit=120, risk_adjusted=75, probability=72, player_score=92,
            confidence=0.80, player_match_confidence="high", floor_profit=-250,
            roi=0.60, total_cost=400,
        )
        self.assertEqual(decision, "KANSKE")

    def test_balanced_high_quality_flip_can_be_strong_buy(self):
        decision = make_decision(
            net_profit=120, risk_adjusted=78, probability=72, player_score=90,
            confidence=0.80, player_match_confidence="high", floor_profit=-20,
            roi=0.48, total_cost=250,
        )
        self.assertEqual(decision, "KÖP (starkt fynd)")


class SaleFormatTests(unittest.TestCase):
    def test_structured_sale_type_is_preferred(self):
        self.assertEqual(detect_sale_type({"sale_type": "Auktion"}), "Auktion")
        self.assertEqual(detect_sale_type({"sale_type": "Köp nu"}), "Köp nu")

    def test_buy_now_has_no_entry_buffer(self):
        cost, buffer = compute_entry_cost(
            {"pris": 100, "sale_type": "Köp nu"},
            129,
        )
        self.assertEqual(cost, 129)
        self.assertEqual(buffer, 0)

    def test_auction_uses_conservative_entry_buffer(self):
        cost, buffer = compute_entry_cost(
            {"pris": 100, "sale_type": "Auktion"},
            129,
        )
        self.assertEqual(buffer, 15)
        self.assertEqual(cost, 144)

    def test_expensive_auction_buffer_is_capped(self):
        cost, buffer = compute_entry_cost(
            {"pris": 1000, "sale_type": "Auktion"},
            1029,
        )
        self.assertEqual(buffer, 75)
        self.assertEqual(cost, 1104)

    def test_auction_analysis_keeps_display_cost_but_uses_buffered_cost(self):
        item = {
            "titel": "Connor Bedard Young Guns rookie",
            "pris": 100,
            "frakt": 29,
            "sale_type": "Auktion",
            "source_category": "hockey",
            "lank": "https://example.invalid/item",
        }
        result = analyze_item(item, sport="hockey", strategy_mode="quick_flip", mode="fast")
        self.assertEqual(result["total_cost"], 129)
        self.assertEqual(result["analysis_total_cost"], 144)
        self.assertEqual(result["auction_buffer"], 15)
        self.assertIn("auktionspris kan stiga före avslut", result["risk_flags"])


class PremiumTraitGuardrailTests(unittest.TestCase):
    def test_demand_factor_rewards_market_demand(self):
        self.assertEqual(collectible_demand_factor(90), 1.0)
        self.assertEqual(collectible_demand_factor(30), 0.25)

    def test_auto_bonus_is_demand_sensitive(self):
        features = {"is_auto": True, "is_patch": False, "is_jersey": False, "is_game_worn": False, "is_1of1": False, "serial_number": None}
        elite_bonus, _, _ = premium_trait_bonus(features, 90)
        weak_bonus, _, _ = premium_trait_bonus(features, 30)
        self.assertEqual(elite_bonus, 24)
        self.assertEqual(weak_bonus, 6)

    def test_low_serial_bonus_is_not_universal_value(self):
        features = {"is_auto": False, "is_patch": False, "is_jersey": False, "is_game_worn": False, "is_1of1": False, "serial_number": 10}
        elite_bonus, _, _ = premium_trait_bonus(features, 90)
        weak_bonus, _, _ = premium_trait_bonus(features, 30)
        self.assertEqual(elite_bonus, 30)
        self.assertLess(weak_bonus, elite_bonus)

    def test_weak_player_premium_title_gets_explicit_risk(self):
        item = {
            "titel": "Mystery Person autograph patch 10/25",
            "pris": 50,
            "frakt": 29,
            "source_category": "hockey",
            "lank": "https://example.invalid/premium",
        }
        result = analyze_item(item, sport="hockey", strategy_mode="quick_flip", mode="fast")
        self.assertIn(
            "premiumegenskaper har begränsad värdeeffekt på svag spelarmarknad",
            result["risk_flags"],
        )


class RookieAndGradingGuardrailTests(unittest.TestCase):
    def test_rookie_bonus_is_demand_sensitive(self):
        features = {"is_rookie": True, "year": 2023, "set_name": "Young Guns"}
        elite_bonus, elite_conf, _, elite_risks = rookie_trait_bonus(features, 90, "high")
        weak_bonus, weak_conf, _, weak_risks = rookie_trait_bonus(features, 30, "high")
        self.assertGreater(elite_bonus, weak_bonus)
        self.assertGreater(elite_conf, weak_conf)
        self.assertIn("rookiekort på svag spelarmarknad", weak_risks)
        self.assertNotIn("rookiekort på svag spelarmarknad", elite_risks)

    def test_unspecific_rookie_label_does_not_raise_confidence(self):
        features = {"is_rookie": True, "year": None, "set_name": None}
        _, confidence, _, risks = rookie_trait_bonus(features, 90, "high")
        self.assertEqual(confidence, 0.0)
        self.assertIn("rookieetikett är inte fullt verifierad mot år/set", risks)

    def test_psa_gem_mint_title_is_parsed(self):
        features = get_features("2023 Connor Bedard Young Guns Rookie PSA GEM MT 10", "hockey")
        self.assertEqual(features["grade"], "PSA 10")
        self.assertEqual(features["grading_company"], "PSA")
        self.assertTrue(features["is_rookie"])

    def test_top_grade_bonus_is_demand_sensitive(self):
        features = {"grade": "PSA 10", "grading_company": "PSA"}
        elite_bonus, _, reasons, _ = grading_trait_bonus(features, 90)
        weak_bonus, _, _, weak_risks = grading_trait_bonus(features, 30)
        self.assertEqual(elite_bonus, 18)
        self.assertLess(weak_bonus, elite_bonus)
        self.assertIn("PSA 10", reasons)
        self.assertIn("graderingspremie begränsas av svag spelarmarknad", weak_risks)

    def test_low_grade_has_no_automatic_premium(self):
        features = {"grade": "PSA 7", "grading_company": "PSA"}
        bonus, confidence, _, risks = grading_trait_bonus(features, 90)
        self.assertEqual(bonus, 0)
        self.assertEqual(confidence, 0.0)
        self.assertIn("lägre grade ger begränsad premie", risks)

    def test_unknown_player_rookie_is_explicitly_risky(self):
        item = {
            "titel": "Mystery Person Rookie RC",
            "pris": 50,
            "frakt": 29,
            "source_category": "hockey",
            "lank": "https://example.invalid/rookie",
        }
        result = analyze_item(item, sport="hockey", strategy_mode="quick_flip", mode="fast")
        self.assertIn("rookiekort på svag spelarmarknad", result["risk_flags"])
        self.assertIn("rookieetikett är inte fullt verifierad mot år/set", result["risk_flags"])


class RookieProgramHierarchyTests(unittest.TestCase):
    def test_young_guns_is_rookie_without_explicit_rc_text(self):
        features = get_features("2023 Connor Bedard Young Guns #451", "hockey")
        self.assertTrue(features["is_rookie"])
        self.assertEqual(features["rookie_variant"], "Young Guns")
        self.assertEqual(features["rookie_tier"], "iconic")

    def test_future_watch_auto_is_iconic_rookie_program(self):
        features = get_features("2023 Connor Bedard Future Watch Auto /999", "hockey")
        self.assertTrue(features["is_rookie"])
        self.assertEqual(features["rookie_variant"], "Future Watch Auto")
        self.assertEqual(features["rookie_tier"], "iconic")

    def test_rated_rookie_is_detected(self):
        features = get_features("2024 Lamine Yamal Donruss Rated Rookie", "football")
        self.assertTrue(features["is_rookie"])
        self.assertEqual(features["rookie_variant"], "Rated Rookie")
        self.assertEqual(features["rookie_tier"], "strong")

    def test_iconic_rookie_program_beats_generic_rc_for_same_player(self):
        generic = {"is_rookie": True, "rookie_variant": "Generic Rookie", "rookie_tier": "standard", "year": 2023, "set_name": None}
        iconic = {"is_rookie": True, "rookie_variant": "Young Guns", "rookie_tier": "iconic", "year": 2023, "set_name": "Young Guns"}
        generic_bonus, _, _, _ = rookie_trait_bonus(generic, 90, "high")
        iconic_bonus, _, reasons, _ = rookie_trait_bonus(iconic, 90, "high")
        self.assertGreater(iconic_bonus, generic_bonus)
        self.assertIn("rookieprogram: Young Guns", reasons)

    def test_iconic_label_does_not_rescue_weak_player(self):
        features = {"is_rookie": True, "rookie_variant": "Young Guns", "rookie_tier": "iconic", "year": 2023, "set_name": "Young Guns"}
        bonus, _, _, risks = rookie_trait_bonus(features, 30, "high")
        self.assertLess(bonus, 12)
        self.assertIn("känt rookieprogram väger inte upp svag spelarefterfrågan", risks)


if __name__ == "__main__":
    unittest.main()
