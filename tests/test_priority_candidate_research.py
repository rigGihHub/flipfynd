from copy import deepcopy
import pytest

from src import description_price_identity as details
from src.priority_candidate_research import complete_priority_research, research_report
from src.card_parser import parse_card_features
from src.analyzer import get_listing_features
from src.asking_price_opportunity import asking_research_identity, price_lookup_query
from src.ebay_browse_context import match_active_rows


def item(n=1, title='Noni Madueke /10- Panini Prizm Premier League'):
    return {'titel': title, 'lank': f'https://www.tradera.com/item/293311/{n}/card',
            'pris': 100, 'beslut': 'SKIP', 'source_category': 'Fotboll'}


def primary(row, description):
    return dict(row, full_description=description, purchase_detail_verified=True,
                purchase_detail_url=row['lank'], purchase_detail_item_id=row['lank'].split('/')[5])


@pytest.fixture(autouse=True)
def empty_cache():
    details._DETAIL_CACHE.clear()
    yield
    details._DETAIL_CACHE.clear()


def test_visible_candidate_gets_number_and_year_before_price_research_without_buy_promotion():
    raw = item()
    original = deepcopy(raw)
    identities = []
    def verify(row):
        return primary(row, 'Noni Madueke 2023 Panini Prizm Premier League. Kortnummer 17.')
    def enrich(row):
        identities.append(asking_research_identity(row))
        return dict(row, asking_price_opportunity={'comparison_count': 2, 'net_margin': 200})
    rows, debug = complete_priority_research([raw], verifier=verify, enrich=enrich)
    assert identities[0]['card_number'] == '17' and identities[0]['year'] == 2023
    assert rows[0]['beslut'] == 'SKIP' and not rows[0].get('valuation_display_safe')
    assert rows[0]['candidate_research_report']['status'] == 'ACTIVE_CONTEXT'
    assert debug['priority_research_usable'] == 1 and raw == original


def test_priority_is_bounded_and_an_ended_top_card_does_not_reappear():
    rows = [item(n) for n in range(10)]
    calls = []
    def verify(row):
        calls.append(row['lank'])
        return dict(row, listing_inactive=True)
    remaining, debug = complete_priority_research(rows, verifier=verify, enrich=lambda row: row, limit=999)
    assert len(calls) == 5 and len(remaining) == 5
    assert not set(calls) & {row['lank'] for row in remaining}


def test_rate_limit_prevents_all_additional_http_work():
    raw = item()
    raw['asking_price_opportunity'] = {'http_status': 429}
    def unexpected(row):
        raise AssertionError('Must not spend API/detail calls while paused')
    rows, debug = complete_priority_research([raw], verifier=unexpected, enrich=unexpected)
    assert debug['priority_research_api_paused'] and not debug['priority_research_checked']


def test_missing_identity_and_single_price_have_concrete_research_status():
    assert research_report(item())['missing'] == ['år', 'kortnummer']
    row = item(title='Noni Madueke 2023 Panini Prizm Premier League #17 /10')
    row['asking_price_opportunity'] = {'comparison_count': 1}
    assert research_report(row)['status'] == 'SINGLE_PRICE'
    assert research_report(dict(row, listing_inactive=True))['status'] == 'ENDED'


@pytest.mark.parametrize('title,expected', [
    ('Trent Alexander-Arnold /20 Panini Select Prizm', 'Panini Select'),
    ('Noni Madueke /10 Panini Prizm Premier League', 'Panini Prizm'),
    ('Upper Deck Premier 2023-24 Sidney Crosby #1', 'Premier'),
])
def test_parser_and_analyzer_use_same_program(title, expected):
    assert parse_card_features(title)['set_name'] == expected
    assert get_listing_features({'titel': title}, 'football' if 'Panini' in title else 'hockey')['set_name'] == expected


def test_year_and_competition_are_kept_in_queries_matching_and_cache(monkeypatch):
    target = 'Trent Alexander-Arnold 2024 Topps Chrome Euro #17 /24'
    identity = asking_research_identity(item(title=target))
    assert '2024' in price_lookup_query(identity)
    titles = [target, target.replace('2024', '2023'), target.replace('Euro', 'UCL'),
              target.replace('/24', '/99')]
    rows = match_active_rows([{'title': t, 'url': str(n), 'price': 500,
             'buying_options': ['FIXED_PRICE']} for n,t in enumerate(titles)], identity)
    assert [row['url'] for row in rows if row['asking_comparison_eligible']] == ['0']
    from src import ebay_browse_context as ebay
    keys = []
    monkeypatch.setattr(ebay, 'configured_credentials', lambda: ('id', 'secret'))
    monkeypatch.setattr(ebay, 'fetch_once', lambda key, fn: keys.append(key))
    ebay.fetch_configured_ebay_active_context('same query', identity)
    ebay.fetch_configured_ebay_active_context('same query', dict(identity, year=2023))
    assert keys[0] != keys[1]


def test_primary_description_cannot_change_program_year_or_title_card_number():
    row = item(title='Trent Alexander-Arnold 2024 Panini Select #17 /20')
    for description in ['2024 Panini Prizm #17', '2023 Panini Select #17', '2024 Panini Select #18']:
        assert not details.recover_description_identity(primary(row, description))


def test_explicitly_numbered_fraction_is_not_a_release_season():
    features = parse_card_features('Neymar Jr Futera Unique Cult Heroes CH18 numrerad 24/25')
    assert features['serial_number'] == 25 and features['serial_copy_number'] == 24
    assert features['season'] is None and features['year'] is None


def test_checklist_number_never_backtracks_to_a_partial_digit_or_becomes_copy_number():
    features = parse_card_features('Trent Alexander-Arnold 2024 Topps Chrome Euro #17 /24')
    assert features['card_number'] == '17' and features['serial_copy_number'] is None
    assert parse_card_features('Lionel Messi #12/99')['card_number'] is None


def test_research_report_respects_existing_sold_and_identity_conflicts():
    row = item(title='2024 Topps Chrome Euro Lionel Messi #17')
    row.update(valuation_display_safe=True, sold_comparable_count=3)
    assert research_report(row)['status'] == 'SOLD_CONTEXT'
    row['identity_conflicts'] = ['set_name: titel=Topps Chrome / annonsinfo=Panini Prizm']
    row['asking_price_opportunity'] = {'comparison_count': 2}
    assert research_report(row)['status'] == 'IDENTITY_CONFLICT'


def test_recovered_year_is_visible_as_research_and_fx_failure_is_not_a_failed_match():
    from src.card_explanation import build_card_identity_summary
    row = item()
    row['description_research_identity'] = {'year': 2023, 'card_number': '17'}
    summary = build_card_identity_summary(row)
    year = next(fact for fact in summary['rows'] if fact['label'] == 'Säsong / år')
    assert year['value'] == '2023' and year['level'] == 'research'
    assert 'säsong/år' not in summary['missing']
    # Only verified primary detail can supply those fields to price research.
    row = primary(row, '2023 Panini Prizm Premier League #17')
    row['asking_price_opportunity'] = {'comparison_failure_reason': 'NO_CONVERTIBLE_PRICE_OR_FX'}
    assert research_report(row)['status'] == 'PRICE_OR_FX_MISSING'


def test_late_primary_description_conflict_prevents_price_lookup():
    row = item(title='Noni Madueke 2024 Panini Prizm Premier League /10')
    def verify(row):
        return primary(row, 'Noni Madueke 2023 Panini Prizm Premier League #17 /10')
    def unexpected(row):
        raise AssertionError('Conflicted identities cannot spend another comparison lookup')
    rows, debug = complete_priority_research([row], verifier=verify, enrich=unexpected)
    assert rows[0]['candidate_research_report']['status'] == 'IDENTITY_CONFLICT'
    assert debug['priority_research_usable'] == 0
