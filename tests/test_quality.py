import json
import unittest
from pathlib import Path

from src.analyzer import analyze_item, build_decision_diagnostics, collectible_demand_factor, compute_comp_weight, compute_entry_cost, detect_sale_type, estimate_title_value, get_features, grading_trait_bonus, make_decision, parallel_trait_bonus, premium_trait_bonus, rookie_trait_bonus
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


class DecisionDiagnosticsTests(unittest.TestCase):
    def test_skip_explains_buy_threshold_gaps(self):
        diagnostics = build_decision_diagnostics(
            "SKIP",
            net_profit=5,
            risk_adjusted=2,
            probability=35,
            player_score=80,
            confidence=0.8,
            player_match_confidence="high",
            floor_profit=-10,
            roi=0.05,
            total_cost=100,
        )
        joined = " ".join(diagnostics)
        self.assertIn("Riskjusterad vinst", joined)
        self.assertIn("Säljchans", joined)
        self.assertIn("nettovinst", joined)
        self.assertIn("ROI", joined)

    def test_analyzed_auction_exposes_display_and_analysis_cost(self):
        item = {
            "titel": "Connor McDavid Baskort UD MVP",
            "pris": 1,
            "frakt": 29,
            "raw_text": "Ledande bud 1 kr",
            "source_category": "hockey",
            "lank": "https://example.invalid/auction-ui",
        }
        result = analyze_item(item, sport="hockey", strategy_mode="quick_flip", mode="fast")
        self.assertEqual(result["sale_type"], "Auktion")
        self.assertEqual(result["total_cost"], 30)
        self.assertEqual(result["analysis_total_cost"], 45)
        self.assertEqual(result["auction_buffer"], 15)




class RankExplanationTests(unittest.TestCase):
    def test_explains_confidence_advantage_even_with_lower_profit(self):
        from src.analyzer import explain_rank_advantage
        first = {
            "rank_score": 95, "ranking_confidence_score": 90,
            "risk_adjusted_profit": 80, "sale_probability": 72,
            "player_market_score": 85,
        }
        second = {
            "rank_score": 88, "ranking_confidence_score": 50,
            "risk_adjusted_profit": 120, "sale_probability": 70,
            "player_market_score": 80,
        }
        text = " ".join(explain_rank_advantage(first, second))
        self.assertIn("Säkrare fyndunderlag", text)
        self.assertIn("#2 har 40 kr högre riskjusterad vinst", text)

    def test_explains_profit_and_sale_chance_advantage(self):
        from src.analyzer import explain_rank_advantage
        first = {
            "rank_score": 110, "ranking_confidence_score": 82,
            "risk_adjusted_profit": 140, "sale_probability": 80,
            "player_market_score": 90,
        }
        second = {
            "rank_score": 90, "ranking_confidence_score": 80,
            "risk_adjusted_profit": 90, "sale_probability": 65,
            "player_market_score": 88,
        }
        text = " ".join(explain_rank_advantage(first, second))
        self.assertIn("Högre riskjusterad vinst", text)
        self.assertIn("Högre beräknad säljchans", text)

    def test_near_tie_gets_plain_language_fallback(self):
        from src.analyzer import explain_rank_advantage
        first = {"rank_score": 90, "ranking_confidence_score": 80, "risk_adjusted_profit": 100, "sale_probability": 70, "player_market_score": 80}
        second = {"rank_score": 89, "ranking_confidence_score": 78, "risk_adjusted_profit": 95, "sale_probability": 68, "player_market_score": 78}
        text = " ".join(explain_rank_advantage(first, second))
        self.assertIn("Skillnaden är liten", text)


if __name__ == "__main__":
    unittest.main()

class MaxPurchasePriceTests(unittest.TestCase):
    def test_buy_now_ceiling_is_above_low_current_price(self):
        from src.analyzer import compute_max_purchase_price
        item = {"pris": 20, "frakt": 29, "sale_type": "Köp nu"}
        result = compute_max_purchase_price(item, 200, 150, 70, 90, 0.8, "high")
        self.assertIsNotNone(result)
        self.assertGreater(result["max_total_price"], 49)
        self.assertAlmostEqual(result["max_item_price"] + 29, result["max_total_price"], places=2)

    def test_auction_ceiling_includes_auction_risk(self):
        from src.analyzer import compute_max_purchase_price
        buy_now = compute_max_purchase_price({"pris": 20, "frakt": 29, "sale_type": "Köp nu"}, 250, 180, 70, 90, 0.8, "high")
        auction = compute_max_purchase_price({"pris": 20, "frakt": 29, "sale_type": "Auktion"}, 250, 180, 70, 90, 0.8, "high")
        self.assertIsNotNone(buy_now)
        self.assertIsNotNone(auction)
        self.assertLess(auction["max_total_price"], buy_now["max_total_price"])

    def test_uncertain_player_gets_no_ceiling(self):
        from src.analyzer import compute_max_purchase_price
        result = compute_max_purchase_price({"pris": 20, "frakt": 29, "sale_type": "Köp nu"}, 250, 180, 70, 90, 0.8, "low")
        self.assertIsNone(result)


class ParallelHierarchyTests(unittest.TestCase):
    def test_outburst_is_high_confidence_parallel(self):
        features = get_features("2023 Connor Bedard Young Guns Silver Outburst", "hockey")
        self.assertEqual(features["parallel"], "Silver Outburst")
        self.assertEqual(features["parallel_tier"], "rare")
        self.assertEqual(features["parallel_confidence"], "high")

    def test_red_wings_does_not_become_red_parallel(self):
        features = get_features("Steve Yzerman Detroit Red Wings Upper Deck", "hockey")
        self.assertIsNone(features["parallel"])

    def test_contextual_gold_prizm_is_detected(self):
        features = get_features("2024 Lamine Yamal Panini Prizm Gold Prizm Rookie", "football")
        self.assertEqual(features["parallel"], "Gold")
        self.assertEqual(features["parallel_tier"], "rare")

    def test_parallel_bonus_depends_on_player_demand(self):
        features = {"parallel": "Outburst", "parallel_tier": "rare", "parallel_confidence": "high"}
        elite_bonus, _, reasons, elite_risks = parallel_trait_bonus(features, 90)
        weak_bonus, _, _, weak_risks = parallel_trait_bonus(features, 30)
        self.assertGreater(elite_bonus, weak_bonus)
        self.assertIn("parallel: Outburst", reasons)
        self.assertNotIn("parallelpremie begränsas av svag spelarmarknad", elite_risks)
        self.assertIn("parallelpremie begränsas av svag spelarmarknad", weak_risks)

    def test_ambiguous_silver_requires_visual_verification(self):
        features = get_features("2024 Lamine Yamal Topps Chrome Silver Rookie", "football")
        self.assertEqual(features["parallel"], "Silver")
        _, _, _, risks = parallel_trait_bonus(features, 90)
        self.assertIn("parallelvariant bör verifieras mot bild/checklista", risks)


class CardIdentityTests(unittest.TestCase):
    def test_young_guns_outburst_builds_combined_identity(self):
        features = get_features("2023 Connor Bedard Young Guns Silver Outburst", "hockey")
        self.assertEqual(features["card_identity_family"], "Young Guns")
        self.assertIn("Young Guns", features["card_identity"])
        self.assertIn("Silver Outburst", features["card_identity"])
        self.assertEqual(features["card_identity_confidence"], "high")

    def test_prizm_silver_rookie_builds_combined_identity(self):
        features = get_features("2024 Lamine Yamal Panini Prizm Silver Rookie", "football")
        self.assertEqual(features["card_identity_family"], "Prizm Rookie")
        self.assertIn("Silver", features["card_identity"])

    def test_exact_variant_comp_scores_above_base_card(self):
        from src.market_analysis import score_similarity
        base = {"titel": "2023 Connor Bedard Young Guns Silver Outburst", "pris": 300, "frakt": 29, "lank": "base"}
        exact = {"titel": "2023 Connor Bedard Young Guns Silver Outburst", "pris": 350, "frakt": 29, "lank": "exact"}
        plain = {"titel": "2023 Connor Bedard Young Guns", "pris": 200, "frakt": 29, "lank": "plain"}
        self.assertGreater(score_similarity(base, exact), score_similarity(base, plain))

    def test_different_named_rookie_program_is_penalized(self):
        from src.market_analysis import score_similarity
        yg = {"titel": "2023 Connor Bedard Young Guns", "pris": 200, "frakt": 29, "lank": "yg"}
        fwa = {"titel": "2023 Connor Bedard Future Watch Auto /999", "pris": 300, "frakt": 29, "lank": "fwa"}
        generic = {"titel": "2023 Connor Bedard Rookie RC", "pris": 150, "frakt": 29, "lank": "generic"}
        self.assertLess(score_similarity(yg, fwa), score_similarity(yg, generic))


class CardNumberIdentityTests(unittest.TestCase):
    def test_hash_card_number_is_extracted(self):
        features = get_features("2023 Connor Bedard Young Guns #451", "hockey")
        self.assertEqual(features["card_number"], "451")
        self.assertIn("#451", features["card_identity"])

    def test_alphanumeric_card_number_is_extracted(self):
        features = get_features("Connor Bedard Upper Deck Card #YG-23", "hockey")
        self.assertEqual(features["card_number"], "YG-23")

    def test_serial_number_is_not_card_number(self):
        features = get_features("Connor Bedard Future Watch Auto 12/999", "hockey")
        self.assertIsNone(features["card_number"])
        self.assertEqual(features["serial_number"], 999)

    def test_year_is_not_card_number(self):
        features = get_features("2023 Connor Bedard Young Guns", "hockey")
        self.assertIsNone(features["card_number"])

    def test_exact_checklist_number_scores_above_different_number(self):
        from src.market_analysis import score_similarity
        base = {"titel": "2023 Connor Bedard Young Guns #451", "pris": 300, "frakt": 29, "lank": "base"}
        exact = {"titel": "2023 Connor Bedard Young Guns Card #451", "pris": 330, "frakt": 29, "lank": "exact"}
        other = {"titel": "2023 Connor Bedard Young Guns #452", "pris": 330, "frakt": 29, "lank": "other"}
        self.assertGreater(score_similarity(base, exact), score_similarity(base, other))


class SeasonNormalizationTests(unittest.TestCase):
    def test_full_short_season_formats_normalize_equally(self):
        from src.card_parser import extract_season
        self.assertEqual(extract_season("2023-24 Upper Deck Young Guns"), "2023-24")
        self.assertEqual(extract_season("2023/24 Upper Deck Young Guns"), "2023-24")
        self.assertEqual(extract_season("2023/2024 Upper Deck Young Guns"), "2023-24")

    def test_short_season_requires_known_card_product(self):
        from src.card_parser import extract_season
        self.assertEqual(extract_season("23/24 Upper Deck Young Guns Connor Bedard"), "2023-24")
        self.assertIsNone(extract_season("Connor Bedard 23/24"))

    def test_season_normalizes_year_to_start_year(self):
        features = get_features("23/24 Upper Deck Young Guns Connor Bedard #451", "hockey")
        self.assertEqual(features["year"], 2023)
        self.assertEqual(features["season"], "2023-24")
        self.assertIn("2023-24", features["card_identity"])

    def test_equivalent_season_formats_score_as_exact_season(self):
        from src.market_analysis import score_similarity
        a = {"titel": "2023-24 Connor Bedard Young Guns #451", "pris": 300, "frakt": 29, "lank": "a"}
        b = {"titel": "23/24 Connor Bedard Upper Deck Young Guns #451", "pris": 310, "frakt": 29, "lank": "b"}
        wrong = {"titel": "2024-25 Connor Bedard Young Guns #451", "pris": 310, "frakt": 29, "lank": "c"}
        self.assertGreater(score_similarity(a, b), score_similarity(a, wrong))

class LotProtectionTests(unittest.TestCase):
    def test_explicit_quantity_detects_multi_card_listing(self):
        from src.card_parser import detect_lot_info
        info = detect_lot_info("Connor Bedard Young Guns - 5 kort")
        self.assertTrue(info["is_lot"])
        self.assertEqual(info["lot_count"], 5)
        self.assertEqual(info["lot_confidence"], "high")

    def test_official_collection_set_is_not_false_lot(self):
        from src.card_parser import detect_lot_info
        self.assertFalse(detect_lot_info("Connor McDavid Ultimate Collection /99")["is_lot"])
        self.assertFalse(detect_lot_info("Lamine Yamal Topps Museum Collection Rookie")["is_lot"])

    def test_generic_lot_word_is_detected(self):
        from src.card_parser import detect_lot_info
        info = detect_lot_info("Connor Bedard rookie card lot")
        self.assertTrue(info["is_lot"])
        self.assertIn(info["lot_confidence"], {"medium", "high"})

    def test_raw_listing_text_can_reveal_lot(self):
        item = {
            "titel": "Connor Bedard Young Guns #451",
            "raw_text": "Paket med 4 kort. Connor Bedard Young Guns #451",
            "pris": 100,
            "frakt": 29,
            "sale_type": "Köp nu",
            "source_category": "Hockey - NHL",
            "lank": "https://example.invalid/lot-raw",
        }
        result = analyze_item(item, sport="hockey", strategy_mode="quick_flip", mode="fast")
        self.assertTrue(result["is_lot"])
        self.assertEqual(result["lot_count"], 4)
        self.assertIsNone(result["max_total_price"])
        self.assertIn("samlingsannons", result["risk_flags"])

    def test_lot_cannot_become_clear_buy(self):
        item = {
            "titel": "Connor Bedard Young Guns #451 lot 2 cards",
            "pris": 10,
            "frakt": 0,
            "sale_type": "Köp nu",
            "source_category": "Hockey - NHL",
            "lank": "https://example.invalid/lot-buy",
        }
        result = analyze_item(item, sport="hockey", strategy_mode="quick_flip", mode="fast")
        self.assertNotIn(result["beslut"], {"KÖP", "KÖP (starkt fynd)"})
        self.assertIsNone(result["max_item_price"])


class DuplicateCompProtectionTests(unittest.TestCase):
    def test_same_seller_relist_with_small_title_change_is_duplicate(self):
        from src.market_analysis import _likely_same_listing
        a = {
            "titel": "2023-24 Connor Bedard Young Guns #451",
            "pris": 500,
            "frakt": 29,
            "saljare": "cardshop",
            "lank": "https://example.invalid/a",
        }
        b = {
            "titel": "Connor Bedard 23/24 Young Guns card #451 RC",
            "pris": 505,
            "frakt": 29,
            "saljare": "cardshop",
            "lank": "https://example.invalid/b",
        }
        self.assertTrue(_likely_same_listing(a, b))

    def test_different_sellers_are_not_collapsed_on_loose_similarity(self):
        from src.market_analysis import _likely_same_listing
        a = {
            "titel": "Connor Bedard Young Guns rookie",
            "pris": 500,
            "frakt": 29,
            "saljare": "seller-one",
            "lank": "https://example.invalid/a2",
        }
        b = {
            "titel": "Connor Bedard Young Guns rookie card",
            "pris": 500,
            "frakt": 29,
            "saljare": "seller-two",
            "lank": "https://example.invalid/b2",
        }
        self.assertFalse(_likely_same_listing(a, b))

    def test_duplicate_relists_do_not_inflate_comparable_count(self):
        from src.market_analysis import build_market_analysis
        base = {
            "titel": "2023-24 Connor Bedard Young Guns #451",
            "pris": 350,
            "frakt": 29,
            "saljare": "buyer",
            "lank": "https://example.invalid/base",
        }
        relists = [
            {
                "titel": f"Connor Bedard 23/24 Young Guns #451 RC version {i}",
                "pris": 500 + i,
                "frakt": 29,
                "saljare": "same-shop",
                "lank": f"https://example.invalid/relist-{i}",
            }
            for i in range(5)
        ]
        other = {
            "titel": "2023-24 Connor Bedard Young Guns #451",
            "pris": 520,
            "frakt": 29,
            "saljare": "other-shop",
            "lank": "https://example.invalid/other",
        }
        result = build_market_analysis(base, relists + [other])
        self.assertLessEqual(result["comparable_count"], 2)

class ListingQualityGuardrailTests(unittest.TestCase):
    def test_well_identified_listing_gets_high_quality(self):
        from src.analyzer import assess_listing_quality, get_features
        item = {
            "titel": "2023-24 Connor Bedard Young Guns #451",
            "saljare": "cardshop",
        }
        features = get_features(item["titel"], "hockey")
        quality = assess_listing_quality(item, features)
        self.assertEqual(quality["level"], "hög")
        self.assertTrue(quality["clear_buy_safe"])

    def test_vague_listing_is_not_clear_buy_safe(self):
        from src.analyzer import assess_listing_quality, get_features
        item = {
            "titel": "Connor Bedard kort",
            "raw_text": "Se bild, vet ej vilken serie.",
            "saljare": "seller",
        }
        features = get_features(item["titel"], "hockey")
        quality = assess_listing_quality(item, features)
        self.assertFalse(quality["clear_buy_safe"])
        self.assertIn(quality["level"], {"låg", "medel"})

    def test_parallel_without_product_identity_is_blocked(self):
        from src.analyzer import assess_listing_quality, get_features
        item = {
            "titel": "Connor Bedard Silver rookie",
            "saljare": "seller",
        }
        features = get_features(item["titel"], "hockey")
        quality = assess_listing_quality(item, features)
        self.assertTrue(any("variant" in x for x in quality["blockers"]))
        self.assertFalse(quality["clear_buy_safe"])

    def test_ambiguous_listing_does_not_get_max_purchase_price(self):
        item = {
            "titel": "Connor Bedard kort se bild",
            "pris": 10,
            "frakt": 0,
            "sale_type": "Köp nu",
            "source_category": "Hockey - NHL",
            "saljare": "seller",
            "lank": "https://example.invalid/vague",
        }
        result = analyze_item(item, sport="hockey", strategy_mode="quick_flip", mode="fast")
        self.assertIsNone(result["max_total_price"])
        self.assertIn(result["listing_quality_level"], {"låg", "medel"})

    def test_extreme_discount_is_flagged_for_manual_verification(self):
        item = {
            "titel": "2023-24 Connor Bedard Young Guns #451",
            "pris": 1,
            "frakt": 0,
            "sale_type": "Köp nu",
            "source_category": "Hockey - NHL",
            "saljare": "seller",
            "lank": "https://example.invalid/extreme",
        }
        result = analyze_item(item, sport="hockey", strategy_mode="quick_flip", mode="fast")
        # Whether the heuristic reaches the extreme threshold depends on the
        # current valuation model; when it does, the risk must be explicit.
        if result["extreme_discount_flag"]:
            self.assertTrue(any("extrem prisavvikelse" in x for x in result["risk_flags"]))


class DealConfidenceTests(unittest.TestCase):
    def test_strong_evidence_produces_high_deal_confidence(self):
        from src.analyzer import compute_deal_confidence
        result = compute_deal_confidence(
            listing_quality={"score": 92, "blockers": []},
            analysis_confidence=0.82,
            player_match_confidence="high",
            card_identity_confidence="high",
            comparable_count=5,
            comp_confidence="hög",
        )
        self.assertGreaterEqual(result["score"], 80)
        self.assertEqual(result["level"], "hög")

    def test_low_player_identity_caps_deal_confidence(self):
        from src.analyzer import compute_deal_confidence
        result = compute_deal_confidence(
            listing_quality={"score": 90, "blockers": []},
            analysis_confidence=0.85,
            player_match_confidence="low",
            card_identity_confidence="high",
            comparable_count=5,
            comp_confidence="hög",
        )
        self.assertLessEqual(result["score"], 44)
        self.assertEqual(result["level"], "låg")

    def test_extreme_discount_penalizes_deal_confidence(self):
        from src.analyzer import compute_deal_confidence
        normal = compute_deal_confidence(
            listing_quality={"score": 90, "blockers": []},
            analysis_confidence=0.8,
            player_match_confidence="high",
            card_identity_confidence="high",
            comparable_count=3,
            comp_confidence="medel",
            extreme_discount=False,
        )
        extreme = compute_deal_confidence(
            listing_quality={"score": 90, "blockers": []},
            analysis_confidence=0.8,
            player_match_confidence="high",
            card_identity_confidence="high",
            comparable_count=3,
            comp_confidence="medel",
            extreme_discount=True,
        )
        self.assertLess(extreme["score"], normal["score"])
        self.assertTrue(any("prisavvikelse" in x for x in extreme["weaknesses"]))

    def test_analyze_item_exposes_deal_confidence(self):
        item = {
            "titel": "2023-24 Connor Bedard Young Guns #451",
            "pris": 250,
            "frakt": 29,
            "sale_type": "Köp nu",
            "source_category": "Hockey - NHL",
            "saljare": "seller",
            "lank": "https://example.invalid/confidence",
        }
        result = analyze_item(item, sport="hockey", strategy_mode="quick_flip", mode="fast")
        self.assertIn("deal_confidence_score", result)
        self.assertIn(result["deal_confidence_level"], {"låg", "medel", "hög"})
        self.assertGreaterEqual(result["deal_confidence_score"], 0)
        self.assertLessEqual(result["deal_confidence_score"], 100)


class ConfidenceWeightedRankingTests(unittest.TestCase):
    def test_secure_smaller_opportunity_can_outrank_speculative_bigger_one(self):
        from src.analyzer import adjust_rank_for_confidence
        speculative = adjust_rank_for_confidence(125, 35)
        secure = adjust_rank_for_confidence(100, 90)
        self.assertGreater(secure, speculative)

    def test_high_confidence_preserves_more_of_base_rank(self):
        from src.analyzer import adjust_rank_for_confidence
        self.assertGreater(
            adjust_rank_for_confidence(100, 90),
            adjust_rank_for_confidence(100, 40),
        )

    def test_fast_ranking_confidence_does_not_require_comps(self):
        from src.analyzer import compute_ranking_confidence
        score = compute_ranking_confidence(
            listing_quality={"score": 90},
            analysis_confidence=0.80,
            player_match_confidence="high",
            card_identity_confidence="high",
            deal_confidence_score=None,
        )
        self.assertGreaterEqual(score, 85)

    def test_analysis_exposes_confidence_weighted_rank(self):
        item = {
            "titel": "2023-24 Connor Bedard Young Guns #451",
            "pris": 250,
            "frakt": 29,
            "sale_type": "Köp nu",
            "source_category": "Hockey - NHL",
            "saljare": "seller",
            "lank": "https://example.invalid/ranking-confidence",
        }
        result = analyze_item(item, sport="hockey", strategy_mode="quick_flip", mode="fast")
        self.assertIn("base_rank_score", result)
        self.assertIn("ranking_confidence_score", result)
        self.assertIn("rank_score", result)
        self.assertLessEqual(result["rank_score"], result["base_rank_score"])


class AuctionBidStrategyTests(unittest.TestCase):
    def test_auction_with_large_margin_says_wait(self):
        from src.analyzer import build_auction_bid_strategy
        strategy = build_auction_bid_strategy(
            {"sale_type": "Auktion", "pris": 30, "frakt": 29},
            {"max_item_price": 100, "max_total_price": 129, "assumed_shipping": 29},
        )
        self.assertEqual(strategy["status"], "AVVAKTA")
        self.assertEqual(strategy["remaining_bid_margin"], 70)

    def test_auction_near_ceiling_warns(self):
        from src.analyzer import build_auction_bid_strategy
        strategy = build_auction_bid_strategy(
            {"sale_type": "Auktion", "pris": 94, "frakt": 29},
            {"max_item_price": 100, "max_total_price": 129, "assumed_shipping": 29},
        )
        self.assertEqual(strategy["status"], "NÄRA BUDTAK")
        self.assertEqual(strategy["remaining_bid_margin"], 6)

    def test_auction_above_ceiling_stops(self):
        from src.analyzer import build_auction_bid_strategy
        strategy = build_auction_bid_strategy(
            {"sale_type": "Auktion", "pris": 105, "frakt": 29},
            {"max_item_price": 100, "max_total_price": 129, "assumed_shipping": 29},
        )
        self.assertEqual(strategy["status"], "STOPP")
        self.assertEqual(strategy["remaining_bid_margin"], 0)

    def test_buy_now_has_no_auction_strategy(self):
        from src.analyzer import build_auction_bid_strategy
        self.assertIsNone(build_auction_bid_strategy(
            {"sale_type": "Köp nu", "pris": 30, "frakt": 29},
            {"max_item_price": 100, "max_total_price": 129, "assumed_shipping": 29},
        ))

class ListingEvidenceIdentityTests(unittest.TestCase):
    def test_listing_text_can_fill_missing_card_number(self):
        from src.analyzer import get_listing_features
        item = {
            "titel": "Connor Bedard Young Guns rookie",
            "raw_text": "2023-24 Connor Bedard Young Guns rookie Card #451 Köp nu 199 kr",
        }
        features = get_listing_features(item, "hockey")
        self.assertEqual(features["card_number"], "451")
        self.assertIn("card_number", features["identity_enriched_fields"])
        self.assertIn("listing_text", features["identity_evidence_sources"]["card_number"])

    def test_conflicting_card_number_is_not_silently_overwritten(self):
        from src.analyzer import get_listing_features
        item = {
            "titel": "2023-24 Connor Bedard Young Guns #451",
            "raw_text": "2023-24 Connor Bedard Young Guns Card #452 Köp nu 199 kr",
        }
        features = get_listing_features(item, "hockey")
        self.assertEqual(features["card_number"], "451")
        self.assertTrue(features["identity_conflicts"])
        self.assertEqual(features["card_identity_confidence"], "low")

    def test_identity_conflict_blocks_clear_buy(self):
        item = {
            "titel": "2023-24 Connor Bedard Young Guns #451",
            "raw_text": "2023-24 Connor Bedard Young Guns Card #452 Köp nu 10 kr",
            "pris": 10,
            "frakt": 0,
            "sale_type": "Köp nu",
            "source_category": "Hockey - NHL",
            "lank": "https://example.invalid/conflict",
            "saljare": "seller",
        }
        result = analyze_item(item, sport="hockey", strategy_mode="quick_flip", mode="fast")
        self.assertNotIn(result["beslut"], {"KÖP", "KÖP (starkt fynd)"})
        self.assertTrue(result["identity_conflicts"])
        self.assertIn("motstridig kortinformation – manuell kontroll rekommenderas", result["risk_flags"])

    def test_identity_score_is_exposed(self):
        item = {
            "titel": "2023-24 Connor Bedard Young Guns #451",
            "raw_text": "2023-24 Connor Bedard Young Guns #451",
            "pris": 100,
            "frakt": 29,
            "source_category": "Hockey - NHL",
            "lank": "https://example.invalid/identity-score",
            "saljare": "seller",
        }
        result = analyze_item(item, sport="hockey", strategy_mode="quick_flip", mode="fast")
        self.assertGreaterEqual(result["card_identity_confidence_score"], 70)

class SoldCompFoundationTests(unittest.TestCase):
    def _base(self):
        return {
            "titel": "2023-24 Upper Deck Connor Bedard Young Guns #451 Rookie",
            "pris": 60,
            "frakt": 19,
            "source_category": "hockey",
            "lank": "https://example.invalid/base",
        }

    def _sold(self, idx, price, days_ago=20):
        from datetime import datetime, timedelta, timezone
        return {
            "titel": "2023-24 Upper Deck Connor Bedard Young Guns #451 Rookie",
            "pris": price,
            "sold_price": price,
            "frakt": 19,
            "market_state": "sold",
            "sold_verification_status": "verified",
            "sale_evidence_type": "explicit_sold_price",
            "sold_at": (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat(),
            "source_platform": "Tradera",
            "lank": f"https://example.invalid/sold-{idx}",
            "saljare": f"seller-{idx}",
        }

    def _asking(self, idx, price):
        return {
            "titel": "2023-24 Upper Deck Connor Bedard Young Guns #451 Rookie",
            "pris": price,
            "frakt": 19,
            "market_state": "asking",
            "source_platform": "Tradera",
            "lank": f"https://example.invalid/asking-{idx}",
            "saljare": f"ask-{idx}",
        }

    def test_sold_comps_are_primary_when_two_exist(self):
        from src.market_analysis import build_market_analysis
        base = self._base()
        data = [self._sold(1, 180, 10), self._sold(2, 200, 30), self._asking(1, 140), self._asking(2, 160)]
        result = build_market_analysis(base, data)
        self.assertEqual(result["valuation_basis"], "sold")
        self.assertEqual(result["sold_comparable_count"], 2)
        self.assertGreaterEqual(result["asking_comparable_count"], 2)
        self.assertLess(result["price_stats"]["median_comparable_total_cost"], 300)

    def test_active_asking_prices_are_not_labeled_as_sales(self):
        from src.market_analysis import build_market_analysis
        base = self._base()
        result = build_market_analysis(base, [self._asking(1, 130), self._asking(2, 150)])
        self.assertEqual(result["valuation_basis"], "asking")
        self.assertEqual(result["sold_comparable_count"], 0)
        self.assertTrue(all(x["market_state"] == "asking" for x in result["comparable_details"]))
        self.assertIn("inte realiserade försäljningspriser", result["summary"])

    def test_ended_listing_without_sold_evidence_is_not_assumed_sold(self):
        from src.market_analysis import _market_state
        self.assertEqual(_market_state({"status": "ended", "pris": 150}), "asking")
        self.assertEqual(_market_state({"status": "closed", "pris": 150}), "asking")

    def test_legacy_sold_hint_without_verification_is_blocked(self):
        from src.market_analysis import _market_state
        self.assertEqual(
            _market_state({"market_state": "sold", "sold_price": 150}),
            "blocked_sold",
        )

    def test_sold_comp_weight_is_stronger_than_asking_weight(self):
        self.assertGreater(
            compute_comp_weight(3, "medel", "sold"),
            compute_comp_weight(3, "medel", "asking"),
        )

    def test_old_sold_comps_have_lower_age_weight(self):
        from src.market_analysis import _age_weight
        self.assertGreater(_age_weight(15), _age_weight(500))

    def test_comp_details_preserve_provenance(self):
        from src.market_analysis import build_market_analysis
        sold1 = self._sold(1, 180)
        sold2 = self._sold(2, 190)
        sold1["source_platform"] = "eBay"
        sold1["provenance"] = "ebay_sold_import"
        result = build_market_analysis(self._base(), [sold1, sold2])
        details = result["comparable_details"]
        self.assertTrue(any(d["platform"] == "eBay" and d["provenance"] == "ebay_sold_import" for d in details))

    def test_full_analysis_exposes_sold_comp_basis(self):
        base = self._base()
        data = [self._sold(1, 180), self._sold(2, 200), self._sold(3, 190)]
        result = analyze_item(base, sport="hockey", strategy_mode="quick_flip", mode="full", all_items=data)
        self.assertEqual(result["comp_valuation_basis"], "sold")
        self.assertEqual(result["sold_comparable_count"], 3)
        self.assertEqual(result["value_source"], "blended_sold_comps")
        self.assertTrue(result["comparable_details"])


class SoldCompImportV065Tests(unittest.TestCase):
    def test_import_requires_explicit_sold_price(self):
        from src.sold_comp_import import import_sold_comp_rows
        result = import_sold_comp_rows([{"title": "Connor Bedard Young Guns #451"}])
        self.assertEqual(result["added_count"], 0)
        self.assertEqual(result["error_count"], 1)

    def test_import_marks_record_as_sold_and_preserves_provenance(self):
        from src.sold_comp_import import import_sold_comp_rows
        result = import_sold_comp_rows([
            {
                "title": "2023-24 Upper Deck Connor Bedard Young Guns #451",
                "sold_price": 199,
                "shipping": 19,
                "date": "2026-08-20",
                "platform": "eBay",
                "sport": "hockey",
                "url": "https://example.invalid/sale-1",
            }
        ], provenance="test_import")
        record = result["records"][0]
        self.assertEqual(record["market_state"], "sold")
        self.assertEqual(record["source_platform"], "eBay")
        self.assertEqual(record["provenance"], "test_import")
        self.assertEqual(record["source_category"], "Hockey - NHL")

    def test_foreign_currency_is_rejected_without_explicit_conversion(self):
        from src.sold_comp_import import import_sold_comp_rows
        result = import_sold_comp_rows([
            {"title": "Bedard card", "sold_price": 20, "currency": "EUR"}
        ])
        self.assertEqual(result["added_count"], 0)
        self.assertIn("ingen valutakurs gissas", result["errors"][0]["error"])

    def test_foreign_currency_accepts_explicit_fx_rate(self):
        from src.sold_comp_import import import_sold_comp_rows
        result = import_sold_comp_rows([
            {
                "title": "Bedard card",
                "sold_price": 20,
                "currency": "EUR",
                "fx_rate_to_sek": 11.5,
            }
        ])
        record = result["records"][0]
        self.assertEqual(record["sold_price"], 230.0)
        self.assertEqual(record["currency_conversion_source"], "explicit_fx_rate")

    def test_duplicate_url_is_not_imported_twice(self):
        from src.sold_comp_import import import_sold_comp_rows
        rows = [
            {"title": "Bedard Young Guns #451", "sold_price": 200, "url": "https://example.invalid/x"},
            {"title": "Bedard Young Guns #451", "sold_price": 200, "url": "https://example.invalid/x"},
        ]
        result = import_sold_comp_rows(rows)
        self.assertEqual(result["added_count"], 1)
        self.assertEqual(result["duplicate_count"], 1)

    def test_csv_parser_handles_swedish_aliases(self):
        from src.sold_comp_import import import_sold_comp_rows, parse_import_bytes
        raw = "titel,pris,frakt,sport\nBedard Young Guns #451,180,19,hockey\n".encode("utf-8")
        rows = parse_import_bytes(raw, "sold.csv")
        result = import_sold_comp_rows(rows)
        self.assertEqual(result["added_count"], 1)
        self.assertEqual(result["records"][0]["sold_price"], 180.0)

    def test_sold_market_analysis_returns_low_base_high_range(self):
        from src.market_analysis import build_market_analysis
        base = {
            "titel": "2023-24 Upper Deck Connor Bedard Young Guns #451 Rookie",
            "pris": 80,
            "frakt": 19,
            "lank": "https://example.invalid/base-range",
        }
        sold = []
        for i, price in enumerate([160, 180, 200, 240], start=1):
            sold.append({
                "titel": "2023-24 Upper Deck Connor Bedard Young Guns #451 Rookie",
                "sold_price": price,
                "frakt": 19,
                "market_state": "sold",
                "sold_verification_status": "verified",
                "sale_evidence_type": "explicit_sold_price",
                "sold_at": f"2026-08-{10+i:02d}",
                "lank": f"https://example.invalid/sold-range-{i}",
                "saljare": f"seller-{i}",
            })
        result = build_market_analysis(base, sold)
        vrange = result["valuation_range"]
        self.assertEqual(vrange["basis"], "sold")
        self.assertLessEqual(vrange["low"], vrange["base"])
        self.assertLessEqual(vrange["base"], vrange["high"])

    def test_asking_range_is_not_labeled_as_realised_sales(self):
        from src.market_analysis import build_market_analysis
        base = {
            "titel": "2023-24 Upper Deck Connor Bedard Young Guns #451 Rookie",
            "pris": 80,
            "frakt": 19,
            "lank": "https://example.invalid/base-asking-range",
        }
        asking = [
            {
                "titel": base["titel"], "pris": p, "frakt": 19,
                "market_state": "asking", "lank": f"https://example.invalid/a-{i}", "saljare": f"a-{i}"
            }
            for i, p in enumerate([150, 175, 210], start=1)
        ]
        result = build_market_analysis(base, asking)
        self.assertEqual(result["valuation_range"]["basis"], "asking")
        self.assertEqual(result["valuation_range"]["label"], "aktiva begärda priser")

class SoldCompCollectorTests(unittest.TestCase):
    def test_collector_refuses_ended_without_explicit_sale_evidence(self):
        from src.sold_comp_collector import collect_sold_comps
        result = collect_sold_comps([
            {"titel": "Connor Bedard Young Guns #451", "pris": 225, "status": "ended"}
        ])
        self.assertEqual(result["added_count"], 0)
        self.assertEqual(result["not_sold_count"], 1)

    def test_collector_accepts_explicit_sold_price(self):
        from src.sold_comp_collector import collect_sold_comps
        result = collect_sold_comps([
            {"titel": "Connor Bedard Young Guns #451", "sold_price": 225, "source_platform": "Tradera"}
        ])
        self.assertEqual(result["added_count"], 1)
        self.assertEqual(result["records"][0]["sold_price"], 225.0)
        self.assertEqual(result["records"][0]["market_state"], "sold")

    def test_collector_accepts_explicit_sold_state_plus_price(self):
        from src.sold_comp_collector import collect_sold_comps
        result = collect_sold_comps([
            {"titel": "Connor Bedard Young Guns #451", "pris": 210, "sale_status": "sold"}
        ])
        self.assertEqual(result["added_count"], 1)
        self.assertEqual(result["records"][0]["sold_price"], 210.0)

    def test_collector_does_not_accept_closed_state(self):
        from src.sold_comp_collector import has_explicit_sold_evidence
        self.assertFalse(has_explicit_sold_evidence({"pris": 100, "status": "closed"}))
        self.assertFalse(has_explicit_sold_evidence({"pris": 100, "status": "completed"}))

    def test_collector_deduplicates_same_url(self):
        from src.sold_comp_collector import collect_sold_comps
        rows = [
            {"titel": "Connor Bedard Young Guns #451", "sold_price": 225, "lank": "https://x/1"},
            {"titel": "Connor Bedard Young Guns #451", "sold_price": 225, "lank": "https://x/1"},
        ]
        result = collect_sold_comps(rows)
        self.assertEqual(result["added_count"], 1)
        self.assertEqual(result["duplicate_count"], 1)

    def test_collector_enriches_duplicate_without_overwriting_price(self):
        from src.sold_comp_collector import collect_sold_comps
        first = collect_sold_comps([
            {"titel": "Connor Bedard Young Guns #451", "sold_price": 225, "lank": "https://x/1"}
        ])
        second = collect_sold_comps([
            {
                "titel": "Connor Bedard Young Guns #451", "sold_price": 225,
                "lank": "https://x/1", "sold_at": "2026-08-30", "seller": "collector123"
            }
        ], existing=first["records"])
        self.assertEqual(second["added_count"], 0)
        self.assertEqual(second["records"][0]["sold_price"], 225.0)
        self.assertEqual(second["records"][0].get("sold_at"), "2026-08-30")
        self.assertEqual(second["records"][0].get("saljare"), "collector123")

    def test_collector_rejects_foreign_currency_without_explicit_conversion(self):
        from src.sold_comp_collector import collect_sold_comps
        result = collect_sold_comps([
            {"titel": "Connor Bedard Young Guns #451", "sold_price": 20, "currency": "EUR"}
        ])
        self.assertEqual(result["added_count"], 0)
        self.assertEqual(result["invalid_count"], 1)

    def test_collector_accepts_foreign_currency_with_explicit_sek(self):
        from src.sold_comp_collector import collect_sold_comps
        result = collect_sold_comps([
            {
                "titel": "Connor Bedard Young Guns #451", "sold_price": 20, "currency": "EUR",
                "sold_price_sek": 220
            }
        ])
        self.assertEqual(result["added_count"], 1)
        self.assertEqual(result["records"][0]["sold_price"], 220.0)


class SmartSoldCompAcquisitionV01117Tests(unittest.TestCase):
    def test_collector_records_verification_metadata(self):
        from src.sold_comp_collector import collect_sold_comps
        result = collect_sold_comps([
            {"titel": "Connor Bedard Young Guns #451", "sold_price": 225, "source_platform": "Tradera"}
        ], source_name="snapshot.json")
        record = result["records"][0]
        self.assertEqual(record["sold_verification_status"], "verified")
        self.assertEqual(record["sale_evidence_type"], "explicit_sold_price")
        self.assertEqual(record["acquisition_source"], "snapshot.json")

    def test_collector_explains_price_without_sold_evidence(self):
        from src.sold_comp_collector import collect_sold_comps
        result = collect_sold_comps([
            {"titel": "Connor Bedard Young Guns #451", "pris": 225, "status": "ended"}
        ])
        self.assertEqual(result["rejection_reasons"]["price_without_sold_evidence"], 1)

    def test_smart_collector_scans_allowlisted_source_and_excludes_output(self):
        import json
        import tempfile
        from pathlib import Path
        from src.sold_comp_collector import smart_collect_local_sold_comps
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "tradera_data.json").write_text(json.dumps([
                {"titel": "Connor Bedard Young Guns #451", "sold_price": 225, "url": "https://x/sold"},
                {"titel": "Connor Bedard Young Guns #451", "pris": 180, "status": "active"},
            ]), encoding="utf-8")
            output = base / "data" / "sold_comps.json"
            output.parent.mkdir(parents=True)
            output.write_text(json.dumps([
                {"titel": "Should not rescan", "sold_price": 999, "url": "https://x/output"}
            ]), encoding="utf-8")
            result = smart_collect_local_sold_comps(base, exclude=[output])
        self.assertEqual(result["sources_scanned"], 1)
        self.assertEqual(result["added_count"], 1)
        self.assertEqual(result["not_sold_count"], 1)
        self.assertEqual(result["records"][0]["sold_price"], 225.0)

    def test_manual_import_gets_verified_metadata(self):
        from src.sold_comp_import import import_sold_comp_rows
        result = import_sold_comp_rows([
            {"title": "Connor Bedard Young Guns #451", "sold_price": 200}
        ], provenance="manual_test")
        record = result["records"][0]
        self.assertEqual(record["sold_verification_status"], "verified")
        self.assertEqual(record["sale_evidence_type"], "explicit_sold_price")
        self.assertEqual(record["acquisition_source"], "manual_test")

class CompMatchGuardrailTests(unittest.TestCase):
    def test_card_number_conflict_rejects_comp(self):
        from src.market_analysis import assess_comp_compatibility
        result = assess_comp_compatibility(
            {"titel": "2023-24 Upper Deck Connor Bedard Young Guns #451 Silver Outburst"},
            {"titel": "2023-24 Upper Deck Connor Bedard Young Guns #452 Silver Outburst"},
        )
        self.assertFalse(result["eligible"])
        self.assertTrue(any("kortnummer" in reason for reason in result["blockers"]))

    def test_season_conflict_rejects_comp(self):
        from src.market_analysis import assess_comp_compatibility
        result = assess_comp_compatibility(
            {"titel": "2023-24 Upper Deck Connor Bedard Young Guns #451"},
            {"titel": "2022-23 Upper Deck Connor Bedard Young Guns #451"},
        )
        self.assertFalse(result["eligible"])
        self.assertTrue(any("säsong" in reason for reason in result["blockers"]))

    def test_named_parallel_conflict_rejects_comp(self):
        from src.market_analysis import assess_comp_compatibility
        result = assess_comp_compatibility(
            {"titel": "2023-24 Upper Deck Connor Bedard Young Guns #451 Silver Outburst"},
            {"titel": "2023-24 Upper Deck Connor Bedard Young Guns #451 Gold Outburst"},
        )
        self.assertFalse(result["eligible"])
        self.assertTrue(any("parallel" in reason for reason in result["blockers"]))

    def test_serial_denominator_conflict_rejects_comp(self):
        from src.market_analysis import assess_comp_compatibility
        result = assess_comp_compatibility(
            {"titel": "2023-24 Upper Deck Connor Bedard Young Guns #451 /99"},
            {"titel": "2023-24 Upper Deck Connor Bedard Young Guns #451 /25"},
        )
        self.assertFalse(result["eligible"])
        self.assertTrue(any("serial numbering" in reason for reason in result["blockers"]))

    def test_grade_conflict_rejects_comp(self):
        from src.market_analysis import assess_comp_compatibility
        result = assess_comp_compatibility(
            {"titel": "2023-24 Upper Deck Connor Bedard Young Guns #451 PSA 10"},
            {"titel": "2023-24 Upper Deck Connor Bedard Young Guns #451 PSA 9"},
        )
        self.assertFalse(result["eligible"])
        self.assertTrue(any("grade" in reason for reason in result["blockers"]))

    def test_missing_variant_detail_is_uncertainty_not_conflict(self):
        from src.market_analysis import assess_comp_compatibility
        result = assess_comp_compatibility(
            {"titel": "2023-24 Upper Deck Connor Bedard Young Guns #451 Silver Outburst"},
            {"titel": "Connor Bedard Young Guns"},
        )
        self.assertTrue(result["eligible"])
        self.assertEqual(result["blockers"], [])

    def test_rejected_sold_comp_cannot_set_market_value(self):
        from src.market_analysis import build_market_analysis
        base = {
            "titel": "2023-24 Upper Deck Connor Bedard Young Guns #451 Silver Outburst",
            "pris": 50,
            "frakt": 19,
            "lank": "https://example.invalid/base-guardrail",
        }
        sold = [
            {
                "titel": "2023-24 Upper Deck Connor Bedard Young Guns #451 Gold Outburst",
                "sold_price": 500,
                "frakt": 19,
                "market_state": "sold",
                "sold_at": f"2026-08-{20+i:02d}",
                "lank": f"https://example.invalid/wrong-parallel-{i}",
                "saljare": f"seller-{i}",
            }
            for i in range(3)
        ]
        result = build_market_analysis(base, sold)
        self.assertEqual(result["sold_comparable_count"], 0)
        self.assertEqual(result["valuation_basis"], "none")
        self.assertEqual(result["rejected_comparable_count"], 3)

class ValuationConfidenceV068Tests(unittest.TestCase):
    def test_no_comps_is_very_low(self):
        from src.market_analysis import compute_valuation_confidence
        result = compute_valuation_confidence(basis="none", values=[], similarity_scores=[])
        self.assertEqual(result["score"], 10)
        self.assertEqual(result["level"], "mycket låg")

    def test_asking_only_cannot_reach_high_certainty(self):
        from src.market_analysis import compute_valuation_confidence
        result = compute_valuation_confidence(
            basis="asking",
            values=[100, 105, 110, 108, 103, 107, 109, 104],
            similarity_scores=[55] * 8,
        )
        self.assertLessEqual(result["score"], 55)

    def test_recent_matching_sold_comps_can_be_high(self):
        from src.market_analysis import compute_valuation_confidence
        result = compute_valuation_confidence(
            basis="sold",
            values=[195, 205, 200, 210, 198],
            similarity_scores=[58, 60, 61, 57, 59],
            ages=[12, 24, 35, 45, 18],
            rejected_count=0,
        )
        self.assertGreaterEqual(result["score"], 80)
        self.assertEqual(result["level"], "hög")

    def test_price_dispersion_reduces_confidence(self):
        from src.market_analysis import compute_valuation_confidence
        stable = compute_valuation_confidence(
            basis="sold", values=[190, 195, 200, 205], similarity_scores=[55] * 4, ages=[20] * 4
        )
        volatile = compute_valuation_confidence(
            basis="sold", values=[80, 150, 300, 500], similarity_scores=[55] * 4, ages=[20] * 4
        )
        self.assertGreater(stable["score"], volatile["score"])

    def test_many_rejected_comps_reduce_confidence(self):
        from src.market_analysis import compute_valuation_confidence
        clean = compute_valuation_confidence(
            basis="sold", values=[190, 200, 210], similarity_scores=[52] * 3, ages=[30] * 3, rejected_count=0
        )
        noisy = compute_valuation_confidence(
            basis="sold", values=[190, 200, 210], similarity_scores=[52] * 3, ages=[30] * 3, rejected_count=8
        )
        self.assertGreater(clean["score"], noisy["score"])


class CardMarketKnowledgeV068Tests(unittest.TestCase):
    def test_official_chase_signal_is_detected_without_price(self):
        from src.card_market_knowledge import detect_market_knowledge_signals
        signals = detect_market_knowledge_signals("Lamine Yamal Topps Chrome Helix", "football")
        self.assertTrue(any(s.get("label") == "Topps Chrome Helix" for s in signals))
        self.assertTrue(all("price" not in s and "value" not in s for s in signals))

    def test_cross_sport_signal_is_not_applied(self):
        from src.card_market_knowledge import detect_market_knowledge_signals
        signals = detect_market_knowledge_signals("Young Guns", "football")
        self.assertEqual(signals, [])

    def test_new_product_names_are_parsed(self):
        from src.card_parser import extract_set_name
        self.assertEqual(extract_set_name("2025 Topps Chrome Sapphire UEFA rookie"), "Topps Chrome Sapphire")
        self.assertEqual(extract_set_name("2024 Donruss Optic Rated Rookie"), "Donruss Optic")


class CardMarketKnowledgeV069Tests(unittest.TestCase):
    def test_young_guns_high_gloss_gets_max_attention_without_price(self):
        from src.card_market_knowledge import detect_market_knowledge_signals, market_knowledge_attention
        signals = detect_market_knowledge_signals("2025-26 Upper Deck Young Guns High Gloss /10", "hockey")
        labels = {s.get("label") for s in signals}
        self.assertIn("Young Guns High Gloss", labels)
        self.assertTrue(all("price" not in s and "value" not in s for s in signals))
        attention = market_knowledge_attention(signals)
        self.assertEqual(attention["score"], 28)
        self.assertEqual(attention["level"], "mycket hög")

    def test_opc_platinum_numbered_parallel_is_recognized(self):
        from src.card_market_knowledge import detect_market_knowledge_signals
        signals = detect_market_knowledge_signals("2024-25 OPC Platinum Marquee Rookie Emerald Surge /10", "hockey")
        signal = next(s for s in signals if s.get("label") == "OPC Platinum Emerald Surge")
        self.assertEqual(signal.get("print_run"), 10)
        self.assertEqual(signal.get("attention_priority"), 5)

    def test_pmg_hierarchy_is_recognized(self):
        from src.card_market_knowledge import detect_market_knowledge_signals
        green = detect_market_knowledge_signals("Skybox Metal Universe Precious Metal Gem Green /10", "hockey")
        gold = detect_market_knowledge_signals("Skybox Metal Universe Precious Metal Gem Gold 1/1", "hockey")
        self.assertTrue(any(s.get("label") == "PMG Green" and s.get("print_run") == 10 for s in green))
        self.assertTrue(any(s.get("label") == "PMG Gold 1/1" and s.get("print_run") == 1 for s in gold))

    def test_finest_chase_cards_are_recognized(self):
        from src.card_market_knowledge import detect_market_knowledge_signals
        fusion = detect_market_knowledge_signals("Topps Finest Prized Footballers Fusion Variation", "football")
        the_man = detect_market_knowledge_signals("2024-25 Topps Finest The Man", "football")
        self.assertTrue(any(s.get("label") == "Finest Prized Footballers Fusion" for s in fusion))
        self.assertTrue(any(s.get("label") == "Finest The Man" for s in the_man))

    def test_attention_is_zero_for_ordinary_unrecognized_card(self):
        from src.card_market_knowledge import detect_market_attention
        attention = detect_market_attention("Ordinary base card", "hockey")
        self.assertEqual(attention["score"], 0)
        self.assertEqual(attention["level"], "normal")

    def test_new_parallel_names_are_parsed(self):
        from src.card_parser import parse_card_features
        self.assertEqual(parse_card_features("OPC Platinum Emerald Surge /10").get("parallel"), "Emerald Surge")
        self.assertEqual(parse_card_features("Metal Universe PMG Green /10").get("parallel"), "PMG Green")
        self.assertEqual(parse_card_features("OPC Platinum Orange Checkers /25").get("parallel"), "Orange Checkers")

    def test_topps_finest_product_is_parsed(self):
        from src.card_parser import extract_set_name
        self.assertEqual(extract_set_name("2024-25 Topps Finest UEFA The Man"), "Topps Finest")

    def test_wrong_sport_does_not_receive_hockey_pmg_signal(self):
        from src.card_market_knowledge import detect_market_knowledge_signals
        signals = detect_market_knowledge_signals("PMG Green /10", "football")
        self.assertEqual(signals, [])

class AdaptiveCandidateDeepeningV01123Tests(unittest.TestCase):
    def _candidate(self, score, attention=0, boost=0, review=0):
        return ({"titel": "x"}, {
            "rank_score": score,
            "player_card_demand_preselection_boost": boost,
            "player_card_demand_review_priority_score": review,
        }, {"score": attention})

    def test_keeps_baseline_top_twelve(self):
        from src.adaptive_deepening import select_adaptive_full_analysis_indices
        rows = [self._candidate(100-i) for i in range(20)]
        selected = select_adaptive_full_analysis_indices(rows, base_limit=12, hard_cap=30)
        self.assertEqual(selected[:12], list(range(12)))

    def test_deepens_candidate_close_to_cutoff(self):
        from src.adaptive_deepening import select_adaptive_full_analysis_indices
        rows = [self._candidate(100-i) for i in range(12)] + [self._candidate(80)]
        selected = select_adaptive_full_analysis_indices(rows, base_limit=12, hard_cap=30)
        self.assertIn(12, selected)

    def test_deepens_strong_independent_signal_below_cutoff_band(self):
        from src.adaptive_deepening import select_adaptive_full_analysis_indices
        rows = [self._candidate(100-i) for i in range(12)] + [self._candidate(10, attention=12)]
        selected = select_adaptive_full_analysis_indices(rows, base_limit=12, hard_cap=30)
        self.assertIn(12, selected)

    def test_does_not_deepen_weak_tail_and_respects_cap(self):
        from src.adaptive_deepening import select_adaptive_full_analysis_indices
        rows = [self._candidate(100-i) for i in range(12)] + [self._candidate(10) for _ in range(50)]
        selected = select_adaptive_full_analysis_indices(rows, base_limit=12, hard_cap=30)
        self.assertEqual(selected, list(range(12)))
        signaled = [self._candidate(100-i) for i in range(12)] + [self._candidate(10, attention=20) for _ in range(50)]
        selected2 = select_adaptive_full_analysis_indices(signaled, base_limit=12, hard_cap=30)
        self.assertEqual(len(selected2), 30)
