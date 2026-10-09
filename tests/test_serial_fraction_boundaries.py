import pytest

from src.card_parser import extract_serial_number, parse_card_features
from src.candidate_review import build_candidate_review


@pytest.mark.parametrize('fraction,denominator', [
    ('1/1', 1), ('1 / 1', 1), ('1/10', 10), ('11/15', 15),
    ('11/199', 199), ('21/100', 100), ('101/199', 199),
])
def test_one_of_one_requires_complete_fraction(fraction, denominator):
    title = f'Neymar Jr Futera Unique Cult Heroes CH18 numrerad {fraction}'
    assert extract_serial_number(title) == denominator
    features = parse_card_features(title)
    assert features['serial_number'] == denominator
    assert features['is_1of1'] == (denominator == 1)


def test_live_neymar_candidate_uses_actual_title_numbering():
    review = build_candidate_review({
        'titel': 'Neymar Jr - Futera Unique Cult Heroes CH18 numrerad 11/15',
    })
    assert 'Annonsen anger numrering 11/15' in review['reasons']
    assert any('Bekräfta /15 på kortet' in check for check in review['checks'])
