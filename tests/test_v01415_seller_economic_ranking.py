from pathlib import Path

from src.seller_top5 import _seller_opportunity_rank_key, _seller_opportunity_score


def _row(**updates):
    row = {
        "title": "2021-22 Leaf Memories Auto /50",
        "decision": "SKIP",
        "identity_ok": False,
        "sold_comps": 0,
        "deal_score": 0,
        "rank_score": 40,
        "risk_adjusted_profit": -12,
        "collector_signal_score": 35,
        "collector_signals": ["serial_numbered", "autograph"],
        "source_item": {"titel": "2021-22 Leaf Memories Auto 21/50"},
    }
    row.update(updates)
    return row


def test_numbered_autograph_with_negative_economics_is_capped_as_research():
    assert _seller_opportunity_score(_row()) <= 25


def test_positive_economics_rank_before_scarcity_only_candidate():
    scarcity_only = _row()
    economic_candidate = _row(
        title="Verified undervalued card",
        deal_score=62,
        rank_score=55,
        risk_adjusted_profit=140,
        collector_signal_score=0,
        collector_signals=[],
        sold_comps=2,
        identity_ok=True,
        valuation_confidence=70,
        source_item={"titel": "Verified undervalued card"},
    )
    assert _seller_opportunity_rank_key(economic_candidate) > _seller_opportunity_rank_key(scarcity_only)


def test_ui_labels_research_positions_as_research_not_finds():
    app = Path("app.py").read_text(encoding="utf-8")
    assert 'f"Research #{_research_rank}"' in app
    assert "Researchkandidater – inte fynd" in app
