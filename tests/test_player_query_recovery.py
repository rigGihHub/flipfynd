from src.asking_price_opportunity import asking_research_identity


def test_set_and_world_cup_are_not_a_player():
    row = {'titel': '2004-05 Ultimate Collection World Cup of Hockey 203/299 Milan Hejduk #67 Sluttid Imorgon 20:57 . Pris: 28 kr'}
    identity = asking_research_identity(row)
    assert identity['player_name'] == 'Milan Hejduk'
    assert identity['card_number'] == '67'
    assert identity['serial_denominator'] == 299
