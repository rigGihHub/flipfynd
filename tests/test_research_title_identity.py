from src.research_title_identity import build_research_title_identity



def test_recovers_unknown_player_after_explicit_card_number_for_research_only():
    out = build_research_title_identity(
        "2022/23 Topps UCL Super-Stars #100 Jamal Musiala Uncommon Green Pris: 35 kr"
    )
    assert out["fields"]["player_name"] == "Jamal Musiala"
    assert out["fields"]["set_name"] == "Topps UCL Super-Stars"
    assert out["fields"]["card_number"] == "100"


def test_recovers_player_first_title_without_treating_set_as_player():
    out = build_research_title_identity(
        "Nicklas Backstrom 2021-22 MVP Hockey Silver Script #119 Washington Capitals"
    )
    assert out["fields"]["player_name"] in {"Nicklas Backstrom", "Nicklas Bäckström"}
    assert out["fields"]["set_name"] == "MVP"
    assert out["fields"]["card_number"] == "119"


def test_does_not_use_team_words_as_player_after_card_number():
    out = build_research_title_identity(
        "1995-96 Pinnacle #101 Los Angeles Kings Hockey Card"
    )
    # No invented player from a team-only tail.
    assert out["fields"]["player_name"] is None or out["fields"]["player_name"] not in {"Los Angeles", "Angeles Kings"}
