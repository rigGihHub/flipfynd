import unittest
from src.visual_edge import build_visual_edge

class VisualEdgeTests(unittest.TestCase):
    def test_no_image_no_visual_claim(self):
        r=build_visual_edge({"titel":"Connor Bedard Young Guns"})
        self.assertEqual(r["score"],0)
        self.assertFalse(r["requires_visual_verification"])

    def test_weak_listing_with_image_gets_review_priority(self):
        r=build_visual_edge({"titel":"Hockeykort", "image_urls":["https://img.test/1.jpg"]}, listing_quality_score=35, hidden_find_score=70, identity_confidence_score=30)
        self.assertGreaterEqual(r["score"],55)
        self.assertTrue(r["requires_visual_verification"])

    def test_metadata_detail_missing_from_title_is_flagged_not_valued(self):
        r=build_visual_edge({"titel":"Connor Bedard hockeykort", "image_urls":["https://img.test/1.jpg"], "image_alts":["Connor Bedard Young Guns Outburst"]})
        self.assertIn("parallel", r["metadata_terms"])
        for k in ("estimated_value","profit","roi","max_bid"):
            self.assertNotIn(k,r)

    def test_visual_edge_does_not_claim_pixel_detection(self):
        r=build_visual_edge({"titel":"Kort", "image_urls":["https://img.test/1.jpg"]})
        self.assertTrue(r["metadata_only"])

if __name__ == '__main__':
    unittest.main()
