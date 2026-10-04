from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

from src.card_parser import parse_card_features
from src.card_explanation import build_card_identity_summary
from src.collector_evidence import acquisition_breakdown, money, price_evidence, snapshot_notice
from src.seller_bundle_opportunity import (
    find_same_seller_listings, build_shared_shipping_scenario, build_best_same_seller_basket,
)
from src.tradera_purchase_cost import purchase_seller_metadata, verify_purchase_cost
from src.seller_identity import seller_id, seller_url


ORR = '2020-21 Upper Deck Stature Century Momentous Green #CM-5 Bobby Orr /149 Sluttid 23 nov 20:21 . Pris: 67 kr , Köp nu .'


def test_insert_serial_and_colour_are_observations_without_upgrading_saved_gate():
    parsed = parse_card_features(ORR)
    assert parsed['player_name'] == 'Bobby Orr'
    assert parsed['insert_name'] == 'Century Momentous'
    assert parsed['parallel'] == 'Green'
    assert parsed['serial_number'] == 149
    saved = {'titel': ORR, 'player_name': 'Century Momentous',
             'exact_identity_gate_identity_fields': {'player_name': 'Century Momentous'}}
    original = deepcopy(saved)
    summary = build_card_identity_summary(saved)
    rows = {row['label']: row for row in summary['rows']}
    assert rows['Spelare']['value'] == 'Bobby Orr'
    assert '/149' in rows['Numrering']['value']
    assert rows['Insert']['value'] == 'Century Momentous'
    assert not summary['supports_exact_comp_search']
    assert all(row['level'] != 'verified' for row in summary['rows'])
    assert saved == original


def test_colour_and_season_do_not_create_false_parallel_or_numbering():
    assert parse_card_features('2020/21 Stature Bobby Orr Green')['serial_number'] is None
    assert parse_card_features('2020-21 Stature Dylan Larkin Red Wings /149')['parallel'] is None
    assert parse_card_features('2020-21 Upper Deck Bobby Orr Green /149')['parallel'] is None
    assert parse_card_features('2020-21 Stature Bobby Orr Green / 149')['serial_number'] == 149


def test_cost_is_item_shipping_and_fee_and_legacy_gap_is_not_guessed_fee():
    costs = acquisition_breakdown({'pris':67, 'frakt':22, 'buyer_protection_fee':5,
                                  'purchase_cost_verified':True}, 94)
    assert costs['parts'] == [('Kortpris',67), ('Frakt',22), ('Köparskydd',5)]
    assert costs['verified'] and costs['residual'] is None
    legacy = acquisition_breakdown({'pris':67, 'frakt':22},94)
    assert legacy['parts'][2][1] is None
    assert legacy['residual'] == 5
    zero = acquisition_breakdown({'pris':10, 'frakt':0, 'buyer_protection_fee':0},10)
    assert zero['parts'][1:] == [('Frakt',0), ('Köparskydd',0)]


def test_price_links_separate_sold_and_asking_with_currency_dates_and_identity():
    active = {'url':'https://www.ebay.com/itm/123', 'title':ORR, 'price':7.5,
              'currency':'USD','asking_price_sek':80,'condition':'Used'}
    saved = {'asking_price_opportunity':{'comparisons':[active], 'fetched_at':'2026-10-04T12:00:00Z'},
             'ebay_active_context':{'rows':[dict(active,asking_comparison_eligible=True)]},
             'comparable_details':[{'url':'https://www.tradera.com/item/1/456/orr', 'title':ORR,
                                    'market_state':'sold','sold_price':50,'date':'2026-09-30'},
                                   {'url':'javascript:alert(1)','price':999}]}
    evidence = price_evidence(saved)
    assert len(evidence) == 2
    assert evidence[0]['kind'] == 'Begärt pris'
    assert evidence[0]['price'] == '80,00 SEK (7,50 USD)'
    assert 'CM-5' in evidence[0]['identity'] and '/149' in evidence[0]['identity']
    assert evidence[0]['condition'] == 'Used'
    assert '2026-10-04' in evidence[0]['date']
    assert evidence[1]['kind'].startswith('SOLD')
    assert money(7.5,'USD') == '7,50 USD'
    assert '$' not in money(7.5,'USD')


def test_snapshot_distinguishes_old_analysis_from_missing_market():
    text = snapshot_notice({'completed_at':1791115200}, {'total_items':2300},0)
    assert '2300 inlästa annonser' in text and 'Aktuell marknad: 0 annonser' in text
    assert 'sparade analysen' in text and '2026-10-04' in text
    assert 'Okänd tidpunkt' in snapshot_notice({}, {}, 10)


def test_same_seller_uses_canonical_metadata_casefold_and_rejects_conflicting_id():
    anchor = {'seller_alias':'Viennafloyd', 'seller_id':'6180729', 'lank':'anchor','pris':67}
    same = {'seller':{'alias':'viennafloyd','id':'6180729'},'lank':'same','pris':10}
    wrong = dict(same, seller={'alias':'Viennafloyd','id':'999'},lank='wrong')
    out = find_same_seller_listings(anchor,[anchor,same,wrong,dict(same,lank='ended',listing_inactive=True)])
    assert [row['url'] for row in out['rows']] == ['same']


def test_saved_public_inventory_has_canonical_seller_id_and_profile():
    saved = {'saljare':'viennafloyd', 'seller_user_id':'6180729'}
    assert seller_id(saved) == '6180729'
    assert seller_url(saved) == 'https://www.tradera.com/profile/items/6180729/viennafloyd'
    assert seller_url({'saljare':'other'}) is None


def test_public_profile_fallback_is_unambiguous_and_respects_structured_seller():
    one = '<a href="/profile/items/6180729/viennafloyd">Profil</a>'
    other = '<a href="/profile/items/999/other">Annan</a>'
    assert not purchase_seller_metadata({},one)
    assert purchase_seller_metadata({'sellerMemberId':6180729},one)['seller_alias'] == 'viennafloyd'
    assert not purchase_seller_metadata({},one+other)
    matched = purchase_seller_metadata({'seller':{'alias':'Viennafloyd','memberId':6180729}},one+other)
    assert matched['seller_url'].endswith('/6180729/viennafloyd')
    assert 'seller_url' not in purchase_seller_metadata({'sellerAlias':'Wrong'},one)


def test_detail_verification_records_seller_only_for_exact_item():
    detail = {'itemId':123,'sellerAlias':'Viennafloyd','leadingBid':67,
              'paymentCalculations':{'paymentAmountForBid':72},
              'shippingOptions':[{'cost':22,'toCountryCodeIso2':'SE'}]}
    class Response:
        url = 'https://www.tradera.com/item/1/123/card'
        text = '<script>self.__next_f.push('+json.dumps([1,json.dumps({'itemDetails':detail})])+')</script>'
        def raise_for_status(self): pass
    class Session:
        def get(self,*args,**kwargs): return Response()
    out = verify_purchase_cost({'lank':Response.url},session=Session())
    assert out['seller_alias'] == 'Viennafloyd' and out['purchase_checked_at']
    assert out['pris'] + out['frakt'] + out['buyer_protection_fee'] == 94
    wrong = verify_purchase_cost({'lank':'https://www.tradera.com/item/1/456/card'},session=Session())
    assert 'seller_alias' not in wrong


def test_basket_never_claims_budget_without_all_fees_and_shipping():
    current = {'pris':100,'frakt':39,'buyer_protection_fee':5}
    row = {'analysed':True,'decision':'KÖP','identity_ok':True,'sold_comps':2,'potential':80,
           'price':60,'shipping':39,'source_item':{'pris':60,'frakt':39,'buyer_protection_fee':5}}
    assert build_shared_shipping_scenario(current,[row])['scenario_total'] == 209
    assert build_best_same_seller_basket(current,[row],200)['status'] == 'NO_FIT'
    del row['source_item']['buyer_protection_fee']
    assert build_shared_shipping_scenario(current,[row])['scenario_total'] is None
    assert build_best_same_seller_basket(current,[row],500)['excluded_unknown_fee'] == 1
    row['source_item'].update(buyer_protection_fee=5,frakt=None)
    assert build_shared_shipping_scenario(current,[row])['scenario_total'] is None
    assert build_best_same_seller_basket({'pris':100,'frakt':39},[row],500)['status'] == 'INCOMPLETE_ANCHOR'


def test_saved_main_top_five_shows_price_proof_and_complete_cost_without_crash():
    from streamlit.testing.v1 import AppTest
    row = {'titel':ORR,'player_name':'Century Momentous','lank':'https://www.tradera.com/item/1/123/card',
           'pris':67,'frakt':22,'buyer_protection_fee':5,'analysis_total_cost':94,'beslut':'SKIP',
           'asking_price_opportunity':{'status':'RESEARCH_SINGLE_ACTIVE','net_margin':119,'total_cost':94,
              'purchase_price':67,'shipping':22,'shipping_known':True,'buyer_protection_fee':5,
              'reference_asking_price':240,'observed_asking_price':282,'selling_fee':24,'packaging':3,
              'comparison_count':1,'comparisons':[{'url':'https://www.ebay.com/itm/123','title':ORR,'asking_price_sek':282}]}}
    with patch('src.loader.load_data',return_value=[]), patch('importlib.reload',side_effect=lambda module:module):
        app = AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py',default_timeout=30)
        app.session_state['results'] = [row]
        app.session_state['debug'] = {'total_items':2300}
        app.run()
        assert not app.exception
        assert any('Sparad analys: 2300' in x.value for x in app.info)
        rendered = '\n'.join(x.value for x in app.markdown)
        assert 'Köparskydd: 5,00 SEK' in rendered
        assert 'Nettoscenario: 119,00 SEK' in rendered
        assert any('https://www.ebay.com/itm/123' in str(x.proto) for x in app.get('link_button'))
