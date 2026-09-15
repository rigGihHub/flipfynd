from src.card_listing_integrity import assess_listing_integrity
from src.seller_card_merit import assess_seller_card_merit
from src.seller_collector_signals import collector_signals
from src.seller_card_domain import seller_item_domain_check


def test_non_physical_and_proxy_cards_are_hard_exclusions():
    for title in ("Mbappe digital card NFT", "Gretzky custom proxy card", "Jordan replica card"):
        out = assess_listing_integrity(title)
        assert out["eligible_physical_single_card"] is False
        assert assess_seller_card_merit({"title": title, "decision": "KÖP", "sold_comps": 3})["eligible"] is False


def test_reprint_needs_its_own_exact_market_evidence():
    weak = assess_seller_card_merit({"title": "Wayne Gretzky rookie reprint", "collector_signal_score": 20})
    supported = assess_seller_card_merit({
        "title": "Wayne Gretzky rookie reprint", "identity_ok": True, "sold_comps": 2
    })
    assert weak["eligible"] is False
    assert supported["eligible"] is True


def test_sealed_products_are_not_seller_top_five_cards():
    assert seller_item_domain_check({"titel": "2024 Topps Chrome hobby box"})["allowed"] is False


def test_precise_nonstandard_value_drivers_are_detected():
    out = collector_signals({"titel": "Connor Bedard Printing Plate Buyback Photo Variation 1/1"})
    assert {"printing_plate", "buyback", "photo_variation", "one_of_one"} <= set(out["signals"])
