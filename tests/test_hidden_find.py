import unittest
from src.analyzer import compute_hidden_find_signal

class HiddenFindTests(unittest.TestCase):
    def test_generic_title_with_enriched_identity_is_hidden_candidate(self):
        item={"titel":"HOCKEYKORT", "raw_text":"2023-24 Upper Deck Young Guns #451 Connor Bedard"}
        f={"player_name":"Connor Bedard","player_match_type":"fuzzy","player_match_confidence":"medium","identity_enriched_fields":["set_name","season","card_number"]}
        r=compute_hidden_find_signal(item,f,{"score":50},[])
        self.assertTrue(r["is_hidden_candidate"])
        self.assertGreaterEqual(r["score"],55)

    def test_good_specific_title_is_not_hidden(self):
        item={"titel":"2023-24 Upper Deck Young Guns #451 Connor Bedard Rookie", "raw_text":""}
        f={"player_name":"Connor Bedard","player_match_type":"exact","player_match_confidence":"high","identity_enriched_fields":[]}
        r=compute_hidden_find_signal(item,f,{"score":90},[])
        self.assertFalse(r["is_hidden_candidate"])

    def test_hidden_signal_does_not_contain_value_fields(self):
        r=compute_hidden_find_signal({"titel":"FOTBOLLSKORT"},{"identity_enriched_fields":[]},{"score":40},[])
        self.assertNotIn("estimated_value",r)
        self.assertNotIn("max_bid",r)
