import unittest

from src.valuable_card_knowledge import build_valuable_card_knowledge
from src.card_market_knowledge import detect_market_knowledge_signals, load_card_market_knowledge


class ValuableCardKnowledgeTests(unittest.TestCase):
    def test_rpa_is_high_attention_but_not_value_safe(self):
        r = build_valuable_card_knowledge(
            signals=[{"label":"Future Watch Auto Patch /100","category":"rookie_patch_auto","print_run":100}],
            player_name="Star Player", player_market_score=90, variant_rung=4, rookie_rung=5,
            sold_comparable_count=0, valuation_confidence_score=20,
            identity_confidence_score=85, risk_score=35,
        )
        self.assertIn("Rookie Patch Auto", r["archetype"])
        self.assertFalse(r["safe_for_valuation"])
        self.assertEqual(r["market_evidence"], "Otillräckligt underlag")

    def test_weak_player_caps_priority(self):
        r = build_valuable_card_knowledge(
            signals=[{"label":"Rare /10","category":"parallel","print_run":10}],
            player_name="Weak Player", player_market_score=25, variant_rung=5, rookie_rung=0,
            sold_comparable_count=0, valuation_confidence_score=10,
            identity_confidence_score=90, risk_score=30,
        )
        self.assertLess(r["priority_score"], 70)

    def test_sold_comps_change_evidence_not_price_safety(self):
        r = build_valuable_card_knowledge(
            signals=[{"label":"Case Hit","category":"case_hit"}],
            player_name="Star Player", player_market_score=88, variant_rung=5, rookie_rung=0,
            sold_comparable_count=5, valuation_confidence_score=80,
            identity_confidence_score=90, risk_score=25,
        )
        self.assertEqual(r["market_evidence"], "Starkt marknadsstöd")
        self.assertFalse(r["safe_for_valuation"])

    def test_current_young_guns_outburst_gold_knowledge(self):
        load_card_market_knowledge.cache_clear()
        sig = detect_market_knowledge_signals("2025-26 Young Guns Outburst Gold rookie", sport="hockey")
        labels = {x.get("label") for x in sig}
        self.assertIn("Young Guns Outburst Gold 1/1", labels)

    def test_current_chrome_anime_knowledge(self):
        load_card_market_knowledge.cache_clear()
        sig = detect_market_knowledge_signals("2026 Topps Chrome Premier League Chrome Anime", sport="football")
        labels = {x.get("label") for x in sig}
        self.assertIn("Topps Chrome Premier League Chrome Anime", labels)


if __name__ == '__main__':
    unittest.main()
