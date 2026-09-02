import unittest

from src.chase_knowledge_graph import build_chase_knowledge_graph
from src.card_market_knowledge import detect_market_knowledge_signals


class ChaseKnowledgeGraphTests(unittest.TestCase):
    def test_one_of_one_is_high_priority_but_not_value(self):
        signals = detect_market_knowledge_signals(
            "Lamine Yamal Merlins Euro Match Ball Signatures 1/1",
            sport="football",
        )
        graph = build_chase_knowledge_graph(
            signals=signals,
            player_name="Lamine Yamal",
            player_market_score=95,
            features={"card_number": "MY-1"},
        )
        self.assertGreaterEqual(graph["priority_score"], 88)
        self.assertIn("1/1", graph["profile"])
        self.assertFalse(graph["safe_for_valuation"])

    def test_unknown_player_caps_priority(self):
        graph = build_chase_knowledge_graph(
            signals=[{
                "label": "Example 1/1",
                "category": "parallel",
                "print_run": 1,
                "knowledge_tier": 5,
                "attention_priority": 5,
                "product_family": "Example",
            }],
            player_name=None,
            player_market_score=0,
            features={"card_number": "1"},
        )
        self.assertLessEqual(graph["priority_score"], 68)
        self.assertFalse(graph["safe_for_valuation"])

    def test_identity_conflict_caps_graph(self):
        graph = build_chase_knowledge_graph(
            signals=[{
                "label": "High Gloss",
                "category": "parallel",
                "print_run": 10,
                "knowledge_tier": 5,
                "attention_priority": 5,
                "product_family": "Upper Deck",
            }],
            player_name="Connor Bedard",
            player_market_score=99,
            features={"card_number": "451", "identity_conflicts": ["serial mismatch"]},
        )
        self.assertLessEqual(graph["priority_score"], 50)

    def test_museum_grail_signal_is_recognized(self):
        signals = detect_market_knowledge_signals("Topps Museum Grail card", sport="football")
        labels = {s.get("label") for s in signals}
        self.assertIn("Museum Grail Card", labels)

    def test_the_cup_emblems_is_recognized(self):
        signals = detect_market_knowledge_signals("The Cup Emblems of Endorsements", sport="hockey")
        labels = {s.get("label") for s in signals}
        self.assertIn("The Cup Emblems of Endorsements /15", labels)


if __name__ == "__main__":
    unittest.main()
