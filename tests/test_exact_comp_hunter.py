import unittest

from src.exact_comp_hunter import build_exact_query, classify_comp, hunt_exact_comps


IDENTITY = {
    "player_name": "Connor Bedard",
    "set_name": "Upper Deck Series 1",
    "season": "2023-24",
    "card_number": "451",
    "parallel": "Outburst",
}


class ExactCompHunterTests(unittest.TestCase):
    def candidate(self, verified=True):
        return {"verified_identity": verified, "identity_fields": dict(IDENTITY)}

    def sold(self, **updates):
        row = {
            "title": "Connor Bedard 2023-24 Upper Deck Series 1 #451 Outburst",
            "sold_price": 900,
            "market_state": "sold",
            "platform": "test",
            **IDENTITY,
        }
        row.update(updates)
        return row

    def test_query_is_narrow(self):
        q = build_exact_query(IDENTITY)
        self.assertIn("Connor Bedard", q)
        self.assertIn("#451", q)
        self.assertIn("Outburst", q)

    def test_unverified_visual_candidate_cannot_unlock(self):
        result = hunt_exact_comps(self.candidate(False), [self.sold()])
        self.assertFalse(result["unlocked"])
        self.assertEqual(result["exact"], [])

    def test_exact_sold_comp_is_separated(self):
        result = hunt_exact_comps(self.candidate(True), [self.sold()])
        self.assertTrue(result["unlocked"])
        self.assertEqual(result["exact_sold_count"], 1)
        self.assertEqual(result["near_sold_count"], 0)

    def test_parallel_conflict_is_rejected(self):
        row = self.sold(parallel="Gold Outburst", title="Connor Bedard #451 Gold Outburst")
        classified = classify_comp(IDENTITY, row)
        self.assertEqual(classified["tier"], "REJECTED")
        self.assertIn("parallel", classified["conflicts"])

    def test_card_number_conflict_is_rejected(self):
        row = self.sold(card_number="452", title="Connor Bedard #452 Outburst")
        self.assertEqual(classify_comp(IDENTITY, row)["tier"], "REJECTED")

    def test_active_exact_listing_is_not_sold_evidence(self):
        row = self.sold(sold_price=None, market_state="asking", price=999)
        result = hunt_exact_comps(self.candidate(True), [row])
        self.assertEqual(result["exact_sold_count"], 0)

    def test_missing_parallel_becomes_near_not_exact(self):
        row = self.sold(parallel=None, title="Connor Bedard 2023-24 Upper Deck Series 1 #451")
        classified = classify_comp(IDENTITY, row)
        self.assertIn(classified["tier"], {"NEAR", "WEAK"})
        self.assertNotEqual(classified["tier"], "EXACT")


if __name__ == "__main__":
    unittest.main()
