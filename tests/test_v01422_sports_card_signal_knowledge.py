from src.seller_collector_signals import collector_signals
from src.sports_card_signal_knowledge import match_sports_card_signals


def _names(text):
    return {row["name"] for row in match_sports_card_signals(text)}


def test_named_chase_inserts_are_routed_for_checklist_verification():
    assert "named_chase_insert" in _names("Panini Prizm World Cup Manga")
    assert "named_chase_insert" in _names("Upper Deck Day With The Cup")
    out = collector_signals({"titel": "Topps Golden Mirror variation"})
    assert "named_chase_insert" in out["signals"]
    assert out["verify_first"]


def test_elite_parallel_and_premium_structures_are_separate_signals():
    assert "elite_parallel" in _names("Topps Chrome Superfractor")
    assert "premium_autograph_structure" in _names("Rookie Patch Auto RPA")
    assert "premium_relic_structure" in _names("Game used laundry tag")
    assert "premium_issue_variant" in _names("1991 Topps Tiffany")


def test_knowledge_matches_never_create_value_or_buy():
    matches = match_sports_card_signals("Kaboom Superfractor Rookie Patch Auto")
    assert matches
    assert all(row["research_only"] for row in matches)
    assert all(row["creates_value"] is False for row in matches)
    assert all(row["creates_buy"] is False for row in matches)


def test_generic_marketing_words_do_not_match_named_programs():
    assert match_sports_card_signals("Rare amazing premium card investment") == []
