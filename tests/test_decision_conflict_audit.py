import unittest

from src.decision_conflict_audit import audit_decision_conflicts


class DecisionConflictAuditTests(unittest.TestCase):
    def _base(self, **overrides):
        data = dict(
            decision="KÖP",
            deal_score=78,
            risk_score=30,
            liquidity_score=72,
            valuation_confidence_score=75,
            identity_confidence_score=82,
            sale_probability=72,
            net_profit_estimate=160,
            floor_profit_estimate=55,
            risk_adjusted_profit=115,
            roi_estimate=0.65,
            comp_valuation_basis="sold",
            sold_comparable_count=3,
        )
        data.update(overrides)
        return audit_decision_conflicts(**data)

    def test_consistent_buy_stays_buy(self):
        out = self._base()
        self.assertEqual(out["status"], "KONSEKVENT")
        self.assertEqual(out["audited_decision"], "KÖP")
        self.assertFalse(out["downgraded"])
        self.assertTrue(out["allow_max_purchase"])

    def test_high_score_low_liquidity_is_hard_conflict(self):
        out = self._base(deal_score=88, liquidity_score=20)
        self.assertTrue(out["severe_conflict"])
        self.assertEqual(out["audited_decision"], "KANSKE")
        self.assertTrue(any(x["code"] == "high_score_low_liquidity" for x in out["conflicts"]))

    def test_positive_expected_but_bad_floor_can_block_buy(self):
        out = self._base(net_profit_estimate=180, floor_profit_estimate=-80, risk_score=62)
        self.assertTrue(out["severe_conflict"])
        self.assertEqual(out["audited_decision"], "KANSKE")

    def test_three_moderate_conflicts_can_downgrade(self):
        out = self._base(
            deal_score=84,
            risk_score=62,
            liquidity_score=32,
            valuation_confidence_score=52,
            identity_confidence_score=64,
            sale_probability=53,
            net_profit_estimate=140,
            floor_profit_estimate=10,
            risk_adjusted_profit=74,
            roi_estimate=0.70,
            comp_valuation_basis="none",
            sold_comparable_count=0,
        )
        self.assertGreaterEqual(out["moderate_conflict_count"], 3)
        self.assertTrue(out["severe_conflict"])
        self.assertEqual(out["audited_decision"], "KANSKE")

    def test_single_moderate_conflict_warns_but_does_not_block(self):
        out = self._base(deal_score=82, risk_score=62)
        self.assertEqual(out["status"], "BLANDAD")
        self.assertFalse(out["downgraded"])
        self.assertEqual(out["audited_decision"], "KÖP")

    def test_audit_never_upgrades_non_buy(self):
        out = self._base(decision="KANSKE", deal_score=95, risk_score=10)
        self.assertEqual(out["audited_decision"], "KANSKE")
        self.assertFalse(out["downgraded"])


if __name__ == "__main__":
    unittest.main()
