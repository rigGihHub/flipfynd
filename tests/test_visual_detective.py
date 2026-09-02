import unittest

from src.visual_detective import compare_visual_to_listing, response_schema


class VisualDetectiveTests(unittest.TestCase):
    def test_schema_has_no_valuation_fields(self):
        props = response_schema()["properties"]
        forbidden = {"price", "value", "market_value", "roi", "profit", "max_bid", "buy_recommendation"}
        self.assertTrue(forbidden.isdisjoint(props))

    def test_visual_detail_missing_from_title_becomes_discovery(self):
        result = {
            "player_name": "Connor Bedard",
            "set_or_product": "Upper Deck Series 1",
            "season_or_year": "2023-24",
            "card_number": "451",
            "serial_numerator": None,
            "serial_denominator": None,
            "parallel_or_variant": "Outburst",
            "rookie_marker_visible": "yes",
            "autograph_visible": "no",
            "relic_or_patch_visible": "no",
            "grading_company": None,
            "grade": None,
            "overall_confidence": 0.86,
            "needs_back_image": False,
            "visual_clues": ["Outburst pattern visible"],
            "uncertainties": [],
        }
        comp = compare_visual_to_listing(result, "Connor Bedard hockeykort", "")
        self.assertEqual(comp["status"], "Möjlig visuell edge")
        self.assertTrue(any("parallel/variant" in x for x in comp["discoveries"]))
        self.assertFalse(comp["safe_for_valuation"])

    def test_serial_conflict_is_flagged(self):
        result = {
            "player_name": None,
            "set_or_product": None,
            "season_or_year": None,
            "card_number": None,
            "serial_numerator": 12,
            "serial_denominator": 25,
            "parallel_or_variant": None,
            "rookie_marker_visible": "unknown",
            "autograph_visible": "unknown",
            "relic_or_patch_visible": "unknown",
            "grading_company": None,
            "grade": None,
            "overall_confidence": 0.8,
            "needs_back_image": True,
            "visual_clues": [],
            "uncertainties": [],
        }
        comp = compare_visual_to_listing(result, "Kort 12/99", "")
        self.assertEqual(comp["status"], "Konflikt – verifiera innan analys")
        self.assertTrue(comp["conflicts"])

    def test_low_confidence_never_becomes_visual_edge_status(self):
        result = {
            "player_name": "Unknown Guess",
            "set_or_product": None,
            "season_or_year": None,
            "card_number": None,
            "serial_numerator": None,
            "serial_denominator": None,
            "parallel_or_variant": "Gold",
            "rookie_marker_visible": "unknown",
            "autograph_visible": "unknown",
            "relic_or_patch_visible": "unknown",
            "grading_company": None,
            "grade": None,
            "overall_confidence": 0.3,
            "needs_back_image": True,
            "visual_clues": [],
            "uncertainties": ["blurry"],
        }
        comp = compare_visual_to_listing(result, "Hockeykort", "")
        self.assertEqual(comp["status"], "Låg säkerhet – verifiera manuellt")
        self.assertFalse(comp["safe_for_valuation"])


if __name__ == "__main__":
    unittest.main()
