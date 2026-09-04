import unittest

from src.decision_confidence_audit import audit_decision_confidence


class DecisionConfidenceAuditTests(unittest.TestCase):
    def _base(self, **overrides):
        data = dict(
            decision="KÖP",
            valuation_confidence_score=75,
            identity_confidence_score=82,
            deal_confidence_score=72,
            listing_quality_score=80,
            risk_score=25,
            player_match_confidence="high",
            comp_valuation_basis="sold",
            sold_comparable_count=3,
            asking_comparable_count=0,
            exact_identity_gate_status="SÖKBAR",
            valuation_display_safe=True,
            is_lot=False,
            extreme_discount=False,
        )
        data.update(overrides)
        return audit_decision_confidence(**data)

    def test_strong_evidence_keeps_buy(self):
        out = self._base()
        self.assertEqual(out["audited_decision"], "KÖP")
        self.assertFalse(out["downgraded"])
        self.assertTrue(out["allow_max_purchase"])

    def test_thin_valuation_downgrades_buy(self):
        out = self._base(
            valuation_confidence_score=10,
            comp_valuation_basis="none",
            sold_comparable_count=0,
        )
        self.assertEqual(out["audited_decision"], "KANSKE")
        self.assertTrue(out["downgraded"])
        self.assertTrue(out["thin_value_evidence"])
        self.assertFalse(out["allow_max_purchase"])

    def test_asking_prices_need_stronger_support(self):
        out = self._base(
            comp_valuation_basis="current_listings",
            sold_comparable_count=0,
            asking_comparable_count=2,
            valuation_confidence_score=50,
        )
        self.assertEqual(out["audited_decision"], "KANSKE")
        self.assertTrue(any("aktiva annonser" in x for x in out["blockers"]))

    def test_audit_never_upgrades_non_buy(self):
        out = self._base(decision="KANSKE")
        self.assertEqual(out["audited_decision"], "KANSKE")
        self.assertFalse(out["downgraded"])

    def test_weak_identity_blocks_clear_buy(self):
        out = self._base(identity_confidence_score=35)
        self.assertEqual(out["audited_decision"], "KANSKE")
        self.assertTrue(any("kortidentiteten" in x for x in out["blockers"]))

    def test_premium_display_guard_blocks_clear_buy(self):
        out = self._base(valuation_display_safe=False)
        self.assertEqual(out["audited_decision"], "KANSKE")
        self.assertTrue(any("värdet är inte säkert" in x for x in out["blockers"]))


if __name__ == "__main__":
    unittest.main()
