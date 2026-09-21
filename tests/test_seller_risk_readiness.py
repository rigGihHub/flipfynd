"""Risk evidence must survive the full-analysis bridge and final presentation."""
import pytest

from src.deal_readiness import assess_deal_readiness
from src.seller_live_full_analysis import full_analyze_live_seller_item
from src.seller_top5 import build_seller_top5, seller_result_tier, seller_result_badge


def _item():
    return {
        "titel": "2023-24 Upper Deck Hockey Connor McDavid #1",
        "lank": "https://www.tradera.com/item/2933/123456789",
        "pris": 100,
    }


def _analysis(risk):
    return {
        "beslut": "KÖP", "risk_score": risk,
        "exact_identity_gate_supports_exact_comp_search": True,
        "sold_comparable_count": 3, "valuation_confidence_score": 80,
        "rank_score": 90, "risk_adjusted_profit": 100,
    }


@pytest.fixture(autouse=True)
def no_external_context(monkeypatch):
    monkeypatch.setattr("src.seller_live_full_analysis.configured_credentials", lambda: (None, None))


@pytest.mark.parametrize("risk,tier", [(0, "FIND"), (35, "FIND"), (65, "FIND"), (66, "RESEARCH"), (90, "RESEARCH")])
def test_full_bridge_preserves_risk_and_buy_boundary(risk, tier):
    row = full_analyze_live_seller_item(_item(), analyze_fn=lambda *a, **kw: _analysis(risk))
    assert row.get("risk_score") == risk
    assert seller_result_tier(row) == tier
    assert row["label"] == ("KÖP-KANDIDAT" if tier == "FIND" else "VÄRT ATT UNDERSÖKA")
    if tier != "FIND":
        assert "köprisken är för hög" in row["reason"]


def _compact(**updates):
    row = {"title": _item()["titel"], "decision": "KÖP", "identity_ok": True,
           "sold_comps": 3, "valuation_confidence": 80}
    row.update(updates)
    return row


def test_cached_summary_recovers_high_risk_from_source():
    row = _compact(source_item={**_item(), **_analysis(90)})
    assert assess_deal_readiness(row)["risk_score"] == 90
    assert seller_result_tier(row) == "RESEARCH"


@pytest.mark.parametrize("risk", [None, "", "unknown", float("nan"), float("inf"), -1, 101, True])
def test_unknown_or_invalid_risk_cannot_create_a_find(risk):
    row = _compact(risk_score=risk)
    assert not assess_deal_readiness(row)["ready_for_find"]
    assert "köprisken är inte verifierad" in assess_deal_readiness(row)["blockers"]


def test_missing_risk_cannot_create_a_find():
    assert seller_result_tier(_compact()) == "RESEARCH"


def test_stale_summary_cannot_override_higher_source_risk():
    row = _compact(risk_score=30, source_item={**_item(), **_analysis(90)})
    assert seller_result_tier(row) == "RESEARCH"


@pytest.mark.parametrize("updates,expected", [
    ({"risk_score": 35}, "🟢 KÖP"),
    ({"risk_score": 90}, "🟡 Värt att undersöka"),
    ({"risk_score": 35, "identity_ok": False}, "🟡 Värt att undersöka"),
    ({"risk_score": 35, "sold_comps": 0}, "🟡 Värt att undersöka"),
    ({"risk_score": 35, "valuation_confidence": 40}, "🟡 Värt att undersöka"),
    ({"risk_score": 35, "analysis_level": "quick_fallback"}, "🟡 Värt att undersöka"),
    ({"decision": "SKIP"}, "⚪ Kandidat · ej verifierad"),
])
def test_ui_badge_obeys_final_evidence_gate(updates, expected):
    assert seller_result_badge(_compact(**updates)) == expected


def test_preliminary_fallback_cannot_be_a_verified_find():
    row = _compact(risk_score=30, analysis_level="quick_fallback")
    assert seller_result_tier(row) == "RESEARCH"


def test_seller_pipeline_does_not_publish_high_risk_buy_label():
    result = build_seller_top5("seller", [_item()], analyze_fn=lambda *a, **kw: _analysis(90))
    assert result["full_analysed"] == 1
    row = result["rows"][0]
    assert row["risk_score"] == 90
    assert not row["deal_readiness"]["ready_for_find"]
    assert row["label"] == "VÄRT ATT UNDERSÖKA"
    assert seller_result_tier(row) == "RESEARCH"


def test_positive_profit_without_verified_risk_cannot_get_verified_profit_rank():
    from src.seller_top5 import _seller_opportunity_rank_key
    unsafe = {
        "decision": "UNDERSÖK", "identity_ok": True, "sold_comps": 3,
        "risk_adjusted_profit": 500, "valuation_confidence": 90,
        "rank_score": 99, "player_market_score": 99,
    }
    safe = {
        "decision": "UNDERSÖK", "identity_ok": True, "sold_comps": 1,
        "risk_adjusted_profit": 50, "valuation_confidence": 70, "risk_score": 20,
        "rank_score": 40, "player_market_score": 40,
    }
    assert _seller_opportunity_rank_key(safe) > _seller_opportunity_rank_key(unsafe)


def test_low_valuation_confidence_cannot_get_verified_profit_rank():
    from src.seller_top5 import _seller_opportunity_rank_key
    low_conf = {
        "decision": "UNDERSÖK", "identity_ok": True, "sold_comps": 5,
        "risk_adjusted_profit": 1000, "valuation_confidence": 20, "risk_score": 10,
    }
    verified = {
        "decision": "UNDERSÖK", "identity_ok": True, "sold_comps": 1,
        "risk_adjusted_profit": 40, "valuation_confidence": 70, "risk_score": 20,
    }
    assert _seller_opportunity_rank_key(verified) > _seller_opportunity_rank_key(low_conf)
