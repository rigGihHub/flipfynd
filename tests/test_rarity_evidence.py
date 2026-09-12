from src.card_market_knowledge import detect_market_knowledge_signals
from src.rarity_evidence import grade_rarity_evidence


def test_serial_numbered_signal_is_objective_rarity():
    rows = detect_market_knowledge_signals("2025-26 Young Guns Outburst Red /25", "hockey")
    out = grade_rarity_evidence(rows)
    assert out["exact_rarity_verified"] is True
    assert any(e.get("print_run") == 25 for e in out["evidence"])


def test_published_odds_are_kept_separate_from_price():
    rows = detect_market_knowledge_signals("2025-26 Upper Deck Young Guns Clear Cut", "hockey")
    out = grade_rarity_evidence(rows)
    assert any(e.get("pull_odds") == "1:144 Hobby" for e in out["evidence"])
    assert out["safe_for_valuation"] is False


def test_unsourced_case_hit_claim_gets_warning():
    out = grade_rarity_evidence([{
        "label":"Mystery Case Hit", "category":"case_hit", "rarity_signal":"ultra_rare", "source_id":None
    }])
    assert out["exact_rarity_verified"] is False
    assert out["unsupported_claim_count"] == 1
    assert out["warnings"]


def test_official_chase_does_not_become_ssp_automatically():
    rows = detect_market_knowledge_signals("Topps UCC Roots", "football")
    out = grade_rarity_evidence(rows)
    assert out["exact_rarity_verified"] is False
    assert any(e["kind"] == "manufacturer_chase" for e in out["evidence"])
    assert all("SSP" not in e["status"] for e in out["evidence"] if e["kind"] == "manufacturer_chase")
