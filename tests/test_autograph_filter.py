from src.card_parser import parse_card_features


def test_signature_style_is_not_auto():
    assert parse_card_features("Wayne Rooney Topps Match Attax Legend Signature Style")["is_auto"] is False


def test_silver_script_is_not_auto():
    assert parse_card_features("2021-22 MVP Silver Script Nicklas Backstrom")["is_auto"] is False


def test_explicit_autograph_is_auto():
    assert parse_card_features("Topps Chrome Lionel Messi Autograph /99")["is_auto"] is True


def test_swedish_signed_is_auto():
    assert parse_card_features("Connor McDavid signerad autograf")["is_auto"] is True


def test_explicit_negative_wins():
    assert parse_card_features("Signature card - printed signature - not signed")["is_auto"] is False
