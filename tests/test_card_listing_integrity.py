from src.card_listing_integrity import assess_listing_integrity


def test_lot_title_is_not_an_eligible_single_card():
    result = assess_listing_integrity("Lot 10 Upper Deck hockeykort inklusive Young Guns")
    assert result["eligible_physical_single_card"] is False
    assert "lot_or_multipack" in result["hard_exclusion_reasons"]


def test_explicit_lot_flag_is_respected_even_with_ambiguous_title():
    result = assess_listing_integrity({"titel": "Hockeykort", "is_lot": True})
    assert result["eligible_physical_single_card"] is False
    assert "lot_or_multipack" in result["hard_exclusion_reasons"]


def test_collection_set_name_is_not_mistaken_for_a_lot():
    result = assess_listing_integrity("Lamine Yamal Topps Museum Collection Rookie #100")
    assert result["eligible_physical_single_card"] is True
