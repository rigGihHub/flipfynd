import unittest

from src.card_knowledge_library import build_knowledge_library, explain_library_match


class CardKnowledgeLibraryTests(unittest.TestCase):
    def test_library_groups_young_guns_variants(self):
        library = build_knowledge_library()
        upper = library["products"]["Upper Deck Series"]
        yg = next(p for p in upper["programs"] if p["name"] == "Young Guns")
        labels = {v["label"] for v in yg["variants"]}
        self.assertIn("Young Guns", labels)
        self.assertIn("Young Guns Exclusives", labels)
        self.assertIn("Young Guns High Gloss", labels)
        self.assertGreaterEqual(yg["variant_count"], 4)

    def test_match_explains_sibling_variants(self):
        out = explain_library_match([{
            "label": "Young Guns High Gloss",
            "product_family": "Upper Deck Series",
            "program_family": "Young Guns",
            "print_run": 10,
        }])
        self.assertTrue(out["matched"])
        fam = out["families"][0]
        self.assertEqual(fam["matched_variant"], "Young Guns High Gloss")
        self.assertTrue(any(v["label"] == "Young Guns Exclusives" for v in fam["sibling_variants"]))
        self.assertTrue(any("/10" in x for x in out["comp_boundaries"]))
        self.assertFalse(out["safe_for_valuation"])

    def test_empty_match_is_safe_and_non_valuing(self):
        out = explain_library_match([])
        self.assertFalse(out["matched"])
        self.assertFalse(out["safe_for_valuation"])


if __name__ == "__main__":
    unittest.main()
