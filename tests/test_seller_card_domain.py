from src.seller_card_domain import seller_item_domain_check


def test_series_nytt_comic_is_not_a_trading_card():
    result = seller_item_domain_check({"titel": "1978 Serie Nytt #11"}, sport="hockey")
    assert result["allowed"] is False
    assert result["reason"] == "NOT_A_TRADING_CARD"


def test_explicit_comic_and_magazine_titles_are_blocked():
    for title in ("Marvel Comics #14", "Hockeymagasin 1987", "Serietidning 1979"):
        assert seller_item_domain_check({"titel": title})["allowed"] is False


def test_terse_real_card_listing_is_not_rejected_just_for_missing_card_word():
    result = seller_item_domain_check({"titel": "1986-87 Kraft Dan Daoust"}, sport="hockey")
    assert result["allowed"] is True
