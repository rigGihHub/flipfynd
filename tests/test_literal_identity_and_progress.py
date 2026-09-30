from threading import Event
import time

from src.asking_price_opportunity import asking_research_identity, build_asking_price_opportunity, price_lookup_query
from src.card_parser import parse_card_features
from src.ebay_browse_context import match_active_rows
from src.research_title_identity import build_research_title_identity
from src.search_progress import track_progress, begin_phase, progress_text
from src.inventory_price_sweep import sweep_inventory

GIORDANO = '2020-21 OPC Platinum Rainbow Color Wheel - Mark Giordano Sluttid 1 okt 22:14 . Pris: 10 kr , Köp nu .'


def test_series_number_is_not_a_checklist_number():
    identity = asking_research_identity({'titel': '2021-22 Upper Deck Series 2 Honor Roll Kole Lind'})
    assert identity['player_name'] == 'Kole Lind'
    assert identity['card_number'] is None
    assert asking_research_identity({'titel': '2021-22 Upper Deck Series 2 #451 Kole Lind'})['card_number'] == '451'


def test_dufex_sides_are_distinct_and_unknown_side_cannot_price_a_find():
    target = asking_research_identity({'titel': 'Team Pinnacle 1994-95 #TP9 – Mark Messier (Dufex) / Wayne Gretzky'})
    assert target['parallel'] == 'Dufex Back'
    titles = ['1994-95 Team Pinnacle #TP9 Mark Messier Wayne Gretzky Dufex Back',
              '1994-95 Team Pinnacle #TP9 Mark Messier Wayne Gretzky Dufex Front',
              '1994-95 Team Pinnacle #TP9 Mark Messier Wayne Gretzky Dufex']
    rows = match_active_rows([{'title': title, 'price': 30, 'url': str(i), 'buying_options': ['FIXED_PRICE']}
                              for i, title in enumerate(titles)], target)
    assert [row['url'] for row in rows if row['asking_comparison_eligible']] == ['0']


def test_purchase_detail_uses_exact_item_and_excludes_free_collection():
    import json
    from src.tradera_purchase_cost import verify_purchase_cost
    details = {'itemDetails': {'itemId': 751837261, 'leadingBid': 99, 'openingBid': 99,
        'paymentCalculations': {'paymentAmountForBid': 106}, 'isAuction': True,
        'shippingOptions': [{'cost': 0, 'isTakeaway': True, 'toCountryCodeIso2': 'SE'},
                            {'cost': 49, 'isTakeaway': False, 'toCountryCodeIso2': 'SE'}]}}
    html = '<script>self.__next_f.push(' + json.dumps([1, json.dumps(details)]) + ')</script>'
    class Response:
        text = html
        def raise_for_status(self): pass
    class Session:
        @staticmethod
        def get(*args, **kwargs): return Response()
    item = verify_purchase_cost({'lank': 'https://www.tradera.com/item/293316/751837261/title',
                                 'titel': '1994-95 Team Pinnacle #TP9 Mark Messier Ledande bud', 'pris': 99}, session=Session)
    assert item['frakt'] == 49 and item['buyer_protection_fee'] == 7
    assert item['purchase_cost_verified']
    context = {'rows': [{'price': 300, 'currency': 'SEK', 'url': str(i), 'asking_comparison_eligible': True} for i in range(2)]}
    scenario = build_asking_price_opportunity(item, context)
    assert scenario['total_cost'] == 170  # bid + actual freight + buyer fee + 15 kr bid buffer
    assert scenario['net_margin'] == 56.5
    wrong = verify_purchase_cost({'lank': 'https://www.tradera.com/item/293316/999/title', 'pris': 99}, session=Session)
    assert not wrong.get('purchase_cost_verified')


def test_giordano_never_uses_mcdavid_name_or_auction_date_as_number():
    parsed = parse_card_features(GIORDANO)
    recovered = build_research_title_identity(GIORDANO)
    assert parsed['player_name'] == 'Mark Giordano'
    assert parsed['parallel'] == 'Rainbow Color Wheel'
    assert recovered['fields']['card_number'] is None
    assert not recovered['complete']
    old_gate = {'player_name': 'Rainbow Color', 'card_number': '1'}
    identity = asking_research_identity({'titel': GIORDANO, 'exact_identity_gate_research_identity_fields': old_gate})
    assert identity['player_name'] == 'Mark Giordano'
    assert identity['card_number'] is None
    rows = match_active_rows([{'title': '2020-21 O-Pee-Chee Platinum Rainbow Color Wheel Connor McDavid #1',
        'price': 117, 'url': 'https://www.ebay.com/itm/1', 'buying_options': ['FIXED_PRICE']}], identity)
    assert not any(row.get('asking_comparison_eligible') for row in rows)


def test_literal_bare_number_recovers_same_card_but_wrong_player_number_variant_rejected():
    identity = {'player_name': 'Mark Giordano', 'season': '2020-21', 'set_name': 'OPC Platinum',
                'card_number': '36', 'parallel': 'Rainbow Color Wheel'}
    titles = ['2020-21 O-Pee-Chee Platinum 36 Mark Giordano Rainbow Color Wheel',
              '2020-21 OPC Platinum #1 Connor McDavid Rainbow Color Wheel',
              '2020-21 OPC Platinum #36 Mark Giordano Rainbow',
              '2020-21 OPC Platinum #37 Mark Giordano Rainbow Color Wheel']
    rows = match_active_rows([{'title': title, 'price': 10, 'url': str(i), 'buying_options': ['FIXED_PRICE']}
                              for i, title in enumerate(titles)], identity)
    assert [row['url'] for row in rows if row['asking_comparison_eligible']] == ['0']
    query = price_lookup_query(identity)
    assert 'Mark Giordano' in query and '#36' in query and 'Rainbow Color Wheel' in query
    assert 'OPC' not in query


def test_cheapest_price_cannot_be_discarded_or_duplicate_url_counted_as_evidence():
    item = {'titel': '2020-21 OPC Platinum #36 Mark Giordano Rainbow Color Wheel', 'pris': 10, 'frakt': 29}
    rows = [{'price': p, 'currency': 'USD', 'url': f'https://www.ebay.com/itm/{i}',
             'asking_comparison_eligible': True} for i, p in enumerate([2.29, 12, 14, 15, 20])]
    result = build_asking_price_opportunity(item, {'rows': rows}, fx={'rates_to_sek': {'USD': 10}})
    assert result['observed_asking_price'] == 22.9
    assert result['net_margin'] < 0 and not result['possible_find']
    duplicates = [dict(rows[1], url='https://www.ebay.com/itm/1?q=a'),
                  dict(rows[1], url='https://www.ebay.com/itm/1?q=b')]
    result = build_asking_price_opportunity(item, {'rows': duplicates}, fx={'rates_to_sek': {'USD': 10}})
    assert result['comparison_count'] == 1 and not result['possible_find']


def test_worker_threads_report_coverage_and_eta_without_resetting_existing_progress():
    events = []
    with track_progress(events.append):
        screened, debug = sweep_inventory([{'id': str(i)} for i in range(12)], [], dict, workers=3)
    assert debug['inventory_price_remaining'] == 0
    assert events[-1]['checked'] == events[-1]['total'] == 12
    assert events[-1]['eta_seconds'] == 0
    label, text, fraction = progress_text({'started_at': time.time(), 'progress': events[-1]})
    assert '12 / 12' in text and 'eBay-anrop' in text
    assert label == 'Prisjämför återstående kort' and 0 <= fraction < 1


def test_background_job_saves_progress_and_restores_it_after_disconnect(monkeypatch, tmp_path):
    from src import resumable_search as jobs
    monkeypatch.setattr(jobs, '_ROOT', tmp_path)
    entered, release = Event(), Event()
    token = jobs.new_token()
    def work():
        begin_phase('Prisjämför kort', 20)
        entered.set()
        release.wait(2)
        return [], {}
    assert jobs.start(token, {}, work)
    assert entered.wait(1)
    running = jobs.load(token)
    assert running['progress']['phase'] == 'Prisjämför kort'
    assert running['progress']['total'] == 20
    release.set()
