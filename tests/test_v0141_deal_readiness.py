from src.deal_readiness import assess_deal_readiness
from src.seller_top5 import seller_result_tier


def _row(**updates):
    row = {
        "title": "2015 Upper Deck Young Guns Connor McDavid #201",
        "decision": "KÖP", "identity_ok": True, "sold_comps": 3,
        "valuation_confidence": 75, "risk_score": 35,
    }
    row.update(updates)
    return row


def test_only_evidence_complete_buy_is_a_find():
    assert assess_deal_readiness(_row())["ready_for_find"] is True
    assert seller_result_tier(_row()) == "FIND"


def test_buy_without_identity_is_research_not_find():
    row = _row(identity_ok=False)
    assert assess_deal_readiness(row)["ready_for_find"] is False
    assert seller_result_tier(row) == "RESEARCH"


def test_buy_without_sold_evidence_is_research_not_find():
    row = _row(sold_comps=0)
    assert assess_deal_readiness(row)["ready_for_find"] is False
    assert seller_result_tier(row) == "RESEARCH"


def test_low_valuation_confidence_blocks_find():
    out = assess_deal_readiness(_row(valuation_confidence=40))
    assert out["ready_for_find"] is False
    assert "värderingssäkerheten är under 55/100" in out["blockers"]
