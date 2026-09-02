import unittest
from src.analyzer import compute_opportunity_radar

class OpportunityRadarTests(unittest.TestCase):
    def test_strong_buy_becomes_act_now(self):
        r=compute_opportunity_radar({"beslut":"KÖP","deal_score":82,"market_edge_score":55,"risk_score":30,"valuation_confidence_score":75,"liquidity_score":70,"sale_type":"köp nu"})
        self.assertEqual(r["action"],"AGERA NU")
    def test_high_risk_never_act_now(self):
        r=compute_opportunity_radar({"beslut":"KÖP","deal_score":90,"market_edge_score":70,"risk_score":82,"valuation_confidence_score":80,"liquidity_score":70,"sale_type":"köp nu"})
        self.assertEqual(r["action"],"UNDERSÖK")
    def test_edge_without_buy_evidence_is_investigate(self):
        r=compute_opportunity_radar({"beslut":"SKIP","deal_score":44,"market_edge_score":78,"risk_score":55,"valuation_confidence_score":25,"liquidity_score":40})
        self.assertEqual(r["action"],"UNDERSÖK")
    def test_auction_stop_is_ignore(self):
        r=compute_opportunity_radar({"beslut":"KÖP","deal_score":85,"market_edge_score":50,"risk_score":25,"valuation_confidence_score":80,"liquidity_score":70,"sale_type":"auktion","auction_bid_strategy":{"status":"STOPP"}})
        self.assertEqual(r["action"],"IGNORERA")
    def test_radar_has_no_price_fields(self):
        r=compute_opportunity_radar({"beslut":"KANSKE","deal_score":60,"risk_score":40,"valuation_confidence_score":50})
        for k in ("estimated_value","max_bid","profit","roi"):
            self.assertNotIn(k,r)

if __name__ == "__main__": unittest.main()
