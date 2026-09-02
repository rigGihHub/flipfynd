import unittest

from src.misclassified_card_hunter import build_misclassified_card_signal
from src.card_market_knowledge import detect_market_knowledge_signals, load_card_market_knowledge


class MisclassifiedCardHunterTests(unittest.TestCase):
    def base(self, **overrides):
        kwargs = dict(
            item={"titel": "Connor Bedard hockeykort", "raw_text": "Connor Bedard Young Guns High Gloss /10 #451"},
            features={
                "identity_enriched_fields": ["parallel", "card_number", "serial_number"],
                "identity_confidence_score": 84,
                "identity_conflicts": [],
                "is_lot": False,
            },
            knowledge_signals=[{
                "label": "Young Guns High Gloss /10", "program_family": "Young Guns",
                "category": "numbered_parallel", "rarity_signal": "low_numbered", "print_run": 10,
            }],
            valuable_card_knowledge={"tags": ["Mycket låg numrering"], "priority_score": 90},
            listing_quality={"score": 50},
            hidden_find={"score": 62},
            valuation_confidence_score=35,
            sold_comparable_count=0,
            total_cost=120,
            expected_resale=220,
        )
        kwargs.update(overrides)
        return build_misclassified_card_signal(**kwargs)

    def test_underdescribed_low_numbered_variant_is_candidate(self):
        result = self.base()
        self.assertTrue(result["candidate"])
        self.assertGreaterEqual(result["score"], 70)
        self.assertFalse(result["safe_for_valuation"])

    def test_price_gap_requires_two_sold_and_confidence(self):
        result = self.base(valuation_confidence_score=78, sold_comparable_count=3)
        self.assertTrue(result["price_gap_supported"])
        self.assertIn("Prisgap", result["label"])

    def test_identity_conflict_caps_and_blocks(self):
        features = {
            "identity_enriched_fields": ["parallel", "card_number", "serial_number"],
            "identity_confidence_score": 80,
            "identity_conflicts": ["parallel: titel=base / info=high gloss"],
            "is_lot": False,
        }
        result = self.base(features=features, valuation_confidence_score=90, sold_comparable_count=5)
        self.assertLessEqual(result["score"], 44)
        self.assertFalse(result["candidate"])

    def test_plain_card_without_target_structure_is_ignored(self):
        result = self.base(valuable_card_knowledge={"tags": ["Rookie-program"]})
        self.assertFalse(result["matched"])
        self.assertFalse(result["candidate"])

    def test_future_watch_synonym_pattern_any_matches(self):
        load_card_market_knowledge.cache_clear()
        rows = detect_market_knowledge_signals("Autographed Future Watch Connor Bedard", "hockey")
        self.assertTrue(any(r.get("label") == "Future Watch Autograph" for r in rows))


if __name__ == "__main__":
    unittest.main()

def test_evidence_fusion_conflict_caps_hunter_signal():
    from src.misclassified_card_hunter import build_misclassified_card_signal
    out = build_misclassified_card_signal(
        item={"titel": "Bedard card", "raw_text": "Bedard Young Guns High Gloss /10"},
        features={"identity_confidence_score": 90, "identity_enriched_fields": ["parallel"]},
        knowledge_signals=[{"label": "Young Guns High Gloss", "program_family": "Young Guns"}],
        valuable_card_knowledge={"tags": ["Mycket låg numrering"]},
        listing_quality={"score": 45},
        hidden_find={"score": 70},
        valuation_confidence_score=80,
        sold_comparable_count=3,
        total_cost=100,
        expected_resale=200,
        evidence_fusion={"has_conflict": True, "score": 40, "corroborated_fields": []},
    )
    assert out["score"] <= 42
    assert any("Evidence Fusion" in x for x in out["cautions"])
