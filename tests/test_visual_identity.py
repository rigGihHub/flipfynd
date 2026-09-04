import unittest

from src.visual_identity import build_visual_card_candidates


def finding(**overrides):
    base = {
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
        "overall_confidence": 0.88,
    }
    base.update(overrides)
    return base


class VisualIdentityTests(unittest.TestCase):
    def test_visual_only_candidate_is_never_verified(self):
        result = build_visual_card_candidates(finding())
        self.assertEqual(result["status"], "Kortkandidat behöver verifieras")
        self.assertFalse(result["candidates"][0]["verified_identity"])
        self.assertFalse(result["can_search_exact_comps"])
        self.assertFalse(result["safe_for_valuation"])

    def test_matching_verified_sold_record_can_corroborate_identity(self):
        sold = [{
            "title": "Connor Bedard Upper Deck Series 1 2023-24 #451 Outburst Young Guns",
            "sold_price": 995,
            "market_state": "sold",
            "sold_verification_status": "verified",
            "sale_evidence_type": "explicit_sold_price",
            "platform": "Tradera",
        }]
        result = build_visual_card_candidates(finding(), observed_records=sold)
        self.assertTrue(result["candidates"])
        self.assertTrue(result["candidates"][0]["verified_identity"])
        self.assertTrue(result["can_search_exact_comps"])

    def test_conflicting_card_number_is_rejected(self):
        sold = [{
            "title": "Connor Bedard Upper Deck Series 1 2023-24 #999 Outburst",
            "sold_price": 500,
            "market_state": "sold",
            "sold_verification_status": "verified",
            "sale_evidence_type": "explicit_sold_price",
        }]
        result = build_visual_card_candidates(finding(), observed_records=sold)
        self.assertFalse(any(c["verified_identity"] for c in result["candidates"]))

    def test_unverified_sold_hint_cannot_verify_identity(self):
        sold = [{
            "title": "Connor Bedard Upper Deck Series 1 2023-24 #451 Outburst Young Guns",
            "sold_price": 995,
            "market_state": "sold",
        }]
        result = build_visual_card_candidates(finding(), observed_records=sold)
        self.assertFalse(any(c["verified_identity"] for c in result["candidates"]))

    def test_low_confidence_returns_no_candidate(self):
        result = build_visual_card_candidates(finding(overall_confidence=0.31))
        self.assertEqual(result["status"], "Otillräckligt underlag")
        self.assertTrue(result["blockers"])

    def test_player_missing_blocks_candidate(self):
        result = build_visual_card_candidates(finding(player_name=None))
        self.assertEqual(result["status"], "Otillräckligt underlag")
        self.assertTrue(any("Spelare" in x for x in result["blockers"]))

    def test_candidates_never_mark_safe_for_valuation(self):
        sold = [{
            "title": "Connor Bedard Upper Deck Series 1 2023-24 #451 Outburst",
            "sold_price": 900,
            "market_state": "sold",
            "sold_verification_status": "verified",
            "sale_evidence_type": "explicit_sold_price",
        }]
        result = build_visual_card_candidates(finding(), observed_records=sold)
        self.assertFalse(result["safe_for_valuation"])


if __name__ == "__main__":
    unittest.main()
