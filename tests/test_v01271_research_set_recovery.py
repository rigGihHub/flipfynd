from src.research_title_identity import build_research_title_identity


def test_recovers_unknown_panini_program_between_season_and_card_number():
    out = build_research_title_identity(
        "2023-24 Panini Mosaic Premier League #123 Bukayo Saka Reactive Blue"
    )
    assert out["fields"]["set_name"] == "Panini Mosaic Premier League"
    assert out["fields"]["player_name"] == "Bukayo Saka"
    assert "set/program" in out["recovered_fields"]


def test_recovers_unknown_topps_program_for_research_only():
    out = build_research_title_identity(
        "2022-23 Topps Match Attax UCL #100 Jamal Musiala Green Parallel"
    )
    assert out["fields"]["set_name"] == "Topps Match Attax UCL"
    assert out["fields"]["card_number"] == "100"
    assert out["complete"] is True


def test_recovers_upper_deck_series_product():
    out = build_research_title_identity(
        "2021-22 Upper Deck Series 1 #201 Cole Caufield Young Guns"
    )
    assert out["fields"]["set_name"] == "Upper Deck Series 1"
    assert out["fields"]["player_name"] == "Cole Caufield"


def test_does_not_invent_set_without_brand_anchor():
    out = build_research_title_identity(
        "2022-23 Rare Hockey Card #100 Jamal Musiala Green Parallel"
    )
    assert out["fields"]["set_name"] is None


def test_existing_known_set_still_wins_over_recovery():
    out = build_research_title_identity(
        "1995-96 Pinnacle #101 Wayne Gretzky"
    )
    assert out["fields"]["set_name"] == "Pinnacle"
    assert "set/program" not in out["recovered_fields"]
