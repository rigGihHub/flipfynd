from src.seller_card_merit import assess_seller_card_merit
from src.seller_top5 import seller_result_tier
from src.seller_collector_signals import collector_signals


def test_saka_match_attax_base_is_not_a_find_candidate_despite_star_name():
    row = {"title": "Bukayo Saka Match Attax 2024/2025 Arsenal 24/25 Topps #40", "player_market_score": 95, "sold_comps": 0}
    merit = assess_seller_card_merit(row)
    assert merit["mass_market_base"] is True
    assert merit["eligible"] is False
    assert seller_result_tier(row) == "WEAK"


def test_signature_style_is_not_autograph_or_research_merit():
    row = {"title": "Topps Match Attax 23/24 #412 Pedri Signature Style", "sold_comps": 0}
    merit = assess_seller_card_merit(row)
    assert merit["faux_premium"] is True
    assert merit["eligible"] is False
    assert seller_result_tier(row) == "WEAK"


def test_numbered_match_attax_can_be_researched_but_is_not_automatically_a_find():
    row = {"title": "Haaland Match Attax 2024/25 Red 7/25", "collector_signal_score": 18, "sold_comps": 0}
    merit = assess_seller_card_merit(row)
    assert merit["mass_market_base"] is False
    assert merit["eligible"] is True
    assert seller_result_tier(row) == "RESEARCH"


def test_verified_buy_remains_a_find():
    row = {"title": "Connor McDavid Young Guns Rookie", "decision": "KÖP", "identity_ok": True, "sold_comps": 3, "valuation_confidence": 72, "risk_score": 35, "risk_adjusted_profit": 100}
    assert seller_result_tier(row) == "FIND"


def test_full_and_short_seasons_are_not_serial_numbering():
    assert "serial_numbered" not in collector_signals({"title": "Match Attax 2024/25 Blue Crystal #379"})["signals"]
    assert "serial_numbered" not in collector_signals({"title": "Match Attax 2024/2025 Blue Crystal #379"})["signals"]
    assert "serial_numbered" in collector_signals({"title": "Match Attax 2024/25 Blue Crystal 7/25"})["signals"]


def test_mass_market_team_badge_needs_real_sold_evidence():
    title = "2024/25 Topps Match Attax Blue Crystal Parallel Foil Team Badge #379 Rangers FC"
    merit = assess_seller_card_merit({"title": title, "sold_comps": 0})
    assert merit["mass_market_team_badge"] is True
    assert merit["eligible"] is False
    assert seller_result_tier({"title": title, "sold_comps": 0}) == "WEAK"

    verified = assess_seller_card_merit({"title": title, "sold_comps": 2, "identity_ok": True})
    assert verified["eligible"] is True
