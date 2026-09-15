from src.seller_top5 import _select_hidden_find_exploration


def _row(idx, *, title="Kort", quality=40, price=10):
    return {
        "title": title,
        "price": price,
        "decision": "SKIP",
        "source_item": {
            "titel": title,
            "lank": f"https://www.tradera.com/item/1/{idx}",
            "pris": price,
            "listing_quality_score": quality,
            "listing_quality_warnings": ["kortnummer saknas"],
        },
    }


def test_reserves_four_underdescribed_rows_for_deep_analysis():
    selected = _select_hidden_find_exploration([_row(i) for i in range(10)], slots=4)
    assert len(selected) == 4
    assert all(row["seller_deep_route"] == "HIDDEN_FIND_EXPLORATION" for row in selected)


def test_hard_exclusions_and_condition_damage_are_not_explored():
    rows = [
        _row(1, title="Digital card"),
        _row(2, title="Hockeykort skadad"),
    ]
    assert _select_hidden_find_exploration(rows, slots=4) == []


def test_well_described_low_merit_listing_is_not_forced_into_exploration():
    row = _row(1, title="2022-23 Upper Deck Series 1 Base Card #123 Player Name", quality=90)
    row["source_item"]["listing_quality_warnings"] = []
    assert _select_hidden_find_exploration([row], slots=4) == []
