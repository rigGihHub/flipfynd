from src.pull_frequency_context import parse_published_odds, contextualize_pull_frequency
from src.checklist_collectible_hierarchy import classify_collectible_signal
from src.rarity_evidence import grade_rarity_evidence


def test_parse_pack_odds_keeps_hobby_as_pack_context():
    out = parse_published_odds('1:144 Hobby')
    assert out['denominator'] == 144
    assert out['unit'] == 'pack'


def test_context_converts_pack_odds_when_product_configuration_is_known():
    out = contextualize_pull_frequency({
        'pull_odds': '1:144 Hobby',
        'packs_per_box': 12,
        'boxes_per_case': 12,
    })
    assert out['packs_per_hit'] == 144
    assert out['boxes_per_hit'] == 12
    assert out['cases_per_hit'] == 1
    assert out['frequency_band'] == 'case_level'
    assert out['configuration_complete'] is True


def test_context_does_not_invent_box_or_case_without_configuration():
    out = contextualize_pull_frequency({'pull_odds': '1:1920 Hobby'})
    assert out['packs_per_hit'] == 1920
    assert out['boxes_per_hit'] is None
    assert out['cases_per_hit'] is None
    assert out['frequency_band'] == 'pack_extreme'


def test_direct_case_wording_is_supported():
    out = contextualize_pull_frequency({'pull_odds': '1 per 2 cases'})
    assert out['unit'] == 'case'
    assert out['cases_per_hit'] == 2
    assert out['frequency_band'] == 'case_level'


def test_collectible_hierarchy_exposes_frequency_context():
    c = classify_collectible_signal({
        'label': 'Example chase', 'category': 'insert', 'source_id': 'ud',
        'pull_odds': '1:2880 Hobby', 'packs_per_box': 12, 'boxes_per_case': 12,
    })
    assert c['cases_per_hit'] == 20
    assert c['frequency_band'] == 'multi_case'
    assert c['safe_for_valuation'] is False


def test_rarity_evidence_exposes_case_equivalent_but_not_price():
    out = grade_rarity_evidence([{
        'label': 'Example hit', 'source_id': 'ud', 'pull_odds': '1:144 Hobby',
        'packs_per_box': 12, 'boxes_per_case': 12,
    }])
    e = out['evidence'][0]
    assert e['cases_per_hit'] == 1
    assert e['frequency_band'] == 'case_level'
    assert out['safe_for_valuation'] is False


def test_pipeline_rejects_invalid_product_configuration():
    from src.checklist_knowledge_pipeline import validate_signal
    row = {
        'label':'X', 'sport':'hockey', 'product_family':'P', 'program_family':'X',
        'source_id':'s', 'packs_per_box':0, 'boxes_per_case':'bad'
    }
    errors = validate_signal(row, {'s'})
    assert 'invalid_packs_per_box' in errors
    assert 'invalid_boxes_per_case' in errors
