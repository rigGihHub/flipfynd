from src.card_parser import parse_card_features
from src.seller_card_merit import assess_seller_card_merit
from src.seller_top5 import seller_result_tier


TITLE = "2003-04 Between the Pipes Memorabilia Curtis Sanford"


def test_between_the_pipes_base_card_is_not_invented_as_jersey_or_patch():
    features = parse_card_features(TITLE)
    assert features["set_name"] == "In The Game Between The Pipes"
    assert features["is_patch"] is False
    assert features["is_jersey"] is False


def test_plain_between_the_pipes_card_cannot_fill_seller_top5_without_evidence():
    row = {"title": TITLE, "sold_comps": 0, "decision": "SKIP"}
    assert assess_seller_card_merit(row)["eligible"] is False
    assert seller_result_tier(row) == "WEAK"


def test_explicit_game_used_jersey_still_receives_material_signal():
    features = parse_card_features(TITLE + " Game-Used Jersey")
    assert features["is_jersey"] is True
