import unittest

from src.variant_hierarchy import build_variant_hierarchy


class VariantHierarchyTests(unittest.TestCase):
    def test_young_guns_high_gloss_is_low_numbered_rookie_parallel(self):
        out = build_variant_hierarchy([{
            "label": "Young Guns High Gloss",
            "product_family": "Upper Deck Series",
            "program_family": "Young Guns",
            "category": "rookie_parallel",
            "rarity_signal": "very_low_numbered_flagship_rookie",
            "print_run": 10,
        }])
        self.assertTrue(out["matched"])
        self.assertEqual(out["variant_rung"], 5)
        self.assertEqual(out["rookie_rung"], 3)
        self.assertFalse(out["safe_for_valuation"])

    def test_one_of_one_reaches_top_structural_rung(self):
        out = build_variant_hierarchy([{
            "label": "Prizm Black 1/1",
            "product_family": "Prizm Football",
            "program_family": "Prizm Parallel Family",
            "category": "parallel",
            "rarity_signal": "one_of_one",
            "print_run": 1,
        }])
        self.assertEqual(out["variant_rung"], 6)
        self.assertIn("1/1", out["variant_label"])
        self.assertFalse(out["safe_for_valuation"])

    def test_rookie_patch_auto_sits_above_rookie_auto(self):
        patch = build_variant_hierarchy([{
            "label": "Future Watch Auto Patch /100",
            "category": "rookie_patch_auto",
            "rarity_signal": "premium_numbered_rookie",
            "print_run": 100,
        }])
        auto = build_variant_hierarchy([{
            "label": "Future Watch Autograph /999",
            "category": "rookie_auto",
            "rarity_signal": "numbered_rookie_auto",
            "print_run": 999,
        }])
        self.assertGreater(patch["rookie_rung"], auto["rookie_rung"])
        self.assertEqual(patch["rookie_label"], "Rookie Patch Auto")

    def test_empty_signals_never_value(self):
        out = build_variant_hierarchy([])
        self.assertFalse(out["matched"])
        self.assertEqual(out["variant_rung"], 0)
        self.assertFalse(out["safe_for_valuation"])

    def test_ssp_without_print_run_is_structurally_high_but_not_price_evidence(self):
        out = build_variant_hierarchy([{
            "label": "Prizm Color Blast",
            "category": "ssp_insert",
            "rarity_signal": "ultra_rare_insert",
        }])
        self.assertEqual(out["variant_rung"], 4)
        self.assertIn("SSP", out["variant_label"])
        self.assertFalse(out["safe_for_valuation"])


if __name__ == "__main__":
    unittest.main()
