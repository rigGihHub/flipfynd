import unittest
from src.analyzer import compute_market_edge

class MarketEdgeTests(unittest.TestCase):
    def test_information_gap_and_generic_seller_can_create_edge(self):
        item={"seller_listing_count":8,"seller_generic_title_ratio":0.75}
        hidden={"score":72}
        features={"identity_enriched_fields":["parallel","card_number"],"identity_confidence_score":82}
        result=compute_market_edge(item,hidden,{"score":52},features,{"score":35})
        self.assertTrue(result["is_edge_candidate"])
        self.assertGreaterEqual(result["score"],70)
        self.assertIn("informationsgap",result["types"])

    def test_high_risk_caps_edge(self):
        result=compute_market_edge(
            {"seller_listing_count":10,"seller_generic_title_ratio":0.9},
            {"score":90},{"score":40},
            {"identity_enriched_fields":["parallel"],"identity_confidence_score":90},
            {"score":80},
        )
        self.assertLessEqual(result["score"],55)

    def test_edge_has_no_price_fields(self):
        result=compute_market_edge({}, {"score":0}, {"score":90}, {"identity_enriched_fields":[]}, {"score":20})
        for key in ("estimated_value","max_bid","profit","roi"):
            self.assertNotIn(key,result)

if __name__ == '__main__': unittest.main()
