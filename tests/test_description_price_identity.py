import json

from src.asking_price_opportunity import asking_research_identity, build_asking_price_opportunity
from src.description_price_identity import recover_description_identity, enrich_description_routes
from src.ebay_browse_context import match_active_rows
from src.card_parser import parse_card_features
from src.tradera_purchase_cost import verify_purchase_cost
from src.search_progress import track_progress


def primary(title, description, **extra):
    url = 'https://www.tradera.com/item/293316/751388298/card'
    return dict(titel=title, full_description=description, purchase_detail_verified=True,
                purchase_detail_item_id='751388298', purchase_detail_url=url, lank=url, pris=7, **extra)


def test_live_elias_and_marner_numbers_are_recovered_without_jersey_or_statistics():
    elias = primary('Patrik Elias Silver Script MVP 08-09',
        'Patrik Elias Upper Deck MVP 2008-09 hockeykort. Kortet är nummer 173 i setet. '
        'Elias i tröja nummer 26. Baksidan visar statistik från 1995-96 till 2007-08.')
    assert recover_description_identity(elias) == {'card_number': '173'}
    identity = asking_research_identity(elias)
    assert identity['card_number'] == '173' and identity['season'] == '2008-09'
    marner = primary('Mitch Marner Cast For Greatness 2023-24 Upper Deck Synergy',
        'Mitch Marner 2023-24 Upper Deck Synergy hockeykort. Kortet är märkt CG-4. Samfrakt tre dagar.')
    assert recover_description_identity(marner) == {'card_number': 'CG-4'}


def test_description_cannot_invent_numbers_from_stats_serial_or_another_listing():
    title = 'Mitch Marner 2023-24 Upper Deck Synergy'
    for description in ['Han hade fem poäng i tröja nummer 16.', 'Kortet är numrerat 12/99.',
                        '#12/99', 'Kortet är nummer 4. Ett annat kort är nummer 5.',
                        '2022-23 Upper Deck Synergy #CG-4', '2023-24 OPC Platinum #CG-4']:
        assert not recover_description_identity(primary(title, description))
    assert not recover_description_identity(primary(title, 'Kortet är nummer 4.', listing_inactive=True))
    wrong = primary(title, 'Kortet är nummer 4.')
    wrong['purchase_detail_item_id'] = '999'
    assert not recover_description_identity(wrong)
    wrong['purchase_detail_item_id'] = '751388298'
    wrong['purchase_detail_verified'] = False
    assert not recover_description_identity(wrong)
    assert not recover_description_identity(primary(title + ' #CG-1', '#CG-4'))


def test_missing_season_comes_from_product_not_historical_statistics():
    item = primary('Nikita Okhotiuk OPC Platinum #256',
                   'Nikita Okhotiuk 2022-23 O-Pee-Chee Platinum #256. Baksidan visar statistik från 2020-21.')
    assert recover_description_identity(item) == {'season': '2022-23'}


def test_issue_year_rollover_and_checklist_prefix_do_not_corrupt_player():
    identity = asking_research_identity({'titel': '2021-22 Upper Deck Series 2 Honor Roll #HR-71 Kole Lind'})
    assert identity['player_name'] == 'Kole Lind' and identity['card_number'] == 'HR-71'
    assert identity['set_name'] == 'Upper Deck'
    assert parse_card_features('1999-00 Upper Deck Wayne Gretzky #7')['season'] == '1999-00'
    assert parse_card_features('Valtteri Puustinen Violet Pixels2025-26 O-Pee-Chee Platinum')['season'] == '2025-26'


def test_canonical_set_accepts_exact_young_guns_and_rejects_wrong_insert():
    identity = asking_research_identity({'titel': '2023-24 Upper Deck Series 2 #451 Connor Bedard Young Guns'})
    assert identity['set_name'] == 'Young Guns'
    title = '2023-24 Upper Deck Young Guns Connor Bedard #451'
    assert match_active_rows([dict(title=title, price=10, url='a', buying_options=['FIXED_PRICE'])], identity)[0]['asking_comparison_eligible']
    identity = asking_research_identity({'titel': '2021-22 Upper Deck Series 2 Honor Roll #HR-71 Kole Lind'})
    titles = ['2021-22 Upper Deck Honor Roll Kole Lind #HR-71', '2021-22 Upper Deck Kole Lind #HR-71',
              '2020-21 Upper Deck Honor Roll Kole Lind #HR-71', '2021-22 Upper Deck Honor Roll Kole Lind #HR-72']
    rows = match_active_rows([dict(title=t, price=10, url=str(i), buying_options=['FIXED_PRICE']) for i,t in enumerate(titles)], identity)
    assert [r['url'] for r in rows if r['asking_comparison_eligible']] == ['0']


def test_unavailable_shipping_does_not_discard_primary_description_and_ended_is_excluded():
    detail = {'itemDetails': {'itemId': 751388298, 'title': 'Patrik Elias Silver Script MVP 08-09',
        'description': 'Kortet &#228;r nummer 173.', 'isActive': False, 'hasEnded': True}}
    html = '<script>self.__next_f.push(' + json.dumps([1, json.dumps(detail)]) + ')</script>'
    class Response:
        text = html
        def raise_for_status(self): pass
    class Session:
        @staticmethod
        def get(*args, **kwargs): return Response()
    row = verify_purchase_cost(primary(detail['itemDetails']['title'], ''), session=Session)
    assert row['purchase_detail_verified'] and 'nummer 173' in row['full_description']
    assert row['purchase_cost_verification'] == 'UNAVAILABLE' and row['listing_inactive']
    assert build_asking_price_opportunity(row, {})['status'] == 'LISTING_ENDED'


def test_bounded_description_lane_reports_progress_and_rejects_non_primary_urls():
    from src import description_price_identity as recovery
    recovery._DETAIL_CACHE.clear()
    items = [primary('Patrik Elias Silver Script MVP 08-09', '') for _ in range(3)]
    items.append(dict(titel=items[0]['titel'], lank='https://other.test/item/293316/1/card'))
    calls = []
    def verifier(row):
        calls.append(row)
        return dict(row, full_description='Kortet är nummer 173.')
    events = []
    with track_progress(events.append):
        debug = enrich_description_routes(items, limit=2, verifier=verifier)
    assert len(calls) == 2 and debug['description_identity_recovered'] == 2
    assert debug['description_identity_remaining'] == 1
    assert events[-1]['checked'] == events[-1]['total'] == 2


def test_next_search_reuses_descriptions_and_advances_to_unchecked_ads():
    from src import description_price_identity as recovery
    recovery._DETAIL_CACHE.clear()
    items = []
    for n in range(3):
        row = primary('Patrik Elias Silver Script MVP 08-09', '')
        row.update(lank=f'https://www.tradera.com/item/293316/{n}/card', purchase_detail_item_id=str(n),
                   purchase_detail_url=f'https://www.tradera.com/item/293316/{n}/card')
        items.append(row)
    def verifier(row): return dict(row, full_description='Kortet är nummer 173.')
    first = enrich_description_routes(items, limit=2, verifier=verifier)
    second = enrich_description_routes(items, limit=2, verifier=verifier)
    assert first['description_identity_checked'] == 2
    assert second['description_identity_checked'] == 1 and second['description_identity_reused'] == 2
    assert second['description_identity_recovered'] == 3 and second['description_identity_remaining'] == 0
    recovery._DETAIL_CACHE.clear()
