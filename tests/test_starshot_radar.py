from src.starshot_radar import build_starshot_radar

def ev():
    return {"player_name":"Ada Prospect","sport":"Hockey","event_type":"ranking_rise","source_name":"League","source_url":"https://example.test/a","occurred_at":"2026-09-01T10:00:00Z"}

def test_requires_structured_player_match_and_preserves_decision():
    r=build_starshot_radar([ev()],[{"titel":"Ada Prospect rookie","player_name":"Ada Prospect","decision":"BEVAKA","pris":100,"frakt":29}])
    assert r["matched_card_count"]==1
    card=r["players"][0]["cards"][0]
    assert card["existing_decision"]=="BEVAKA" and card["decision_changed"] is False
    assert card["total_cost"]==129

def test_title_only_does_not_match():
    r=build_starshot_radar([ev()],[{"titel":"Ada Prospect rookie","decision":"KÖP"}])
    assert r["matched_card_count"]==0

def test_market_reaction_is_not_inferred_from_comps():
    r=build_starshot_radar([ev()],[{"player_name":"Ada Prospect","exact_sold_comps":[{"price":200}]}])
    p=r["players"][0]
    assert p["market_reaction_status"]=="Marknadsreaktion ej verifierad"
    assert p["buy_signal_created"] is False
