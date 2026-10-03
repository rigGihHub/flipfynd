from src.asking_price_ui import positive_price_suggestions


def test_all_positive_scenarios_rank_by_net_without_upgrading_one_price_evidence():
    strong = {'titel': 'Ryan', 'lank': 'https://www.tradera.com/item/1/123/card',
              'asking_price_opportunity': {'status': 'POSSIBLE_FIND', 'possible_find': True,
                   'net_margin': 2.17, 'total_cost': 33, 'comparison_count': 2}}
    weak = {'title': 'Rempe', 'url': 'https://www.tradera.com/item/1/456/card',
            'scenario': {'status': 'RESEARCH_SINGLE_ACTIVE', 'possible_find': False,
                         'net_margin': 94.61, 'total_cost': 52, 'comparison_count': 1}}
    rows = positive_price_suggestions([strong], [weak])
    assert [r['titel'] for r in rows] == ['Rempe', 'Ryan']
    assert rows[0]['asking_price_opportunity']['status'] == 'RESEARCH_SINGLE_ACTIVE'
    assert not rows[0]['asking_price_opportunity']['possible_find']
    assert rows[1]['asking_price_opportunity']['possible_find']


def test_one_krona_boundary_duplicates_and_nonfinite_margins():
    def row(url, margin):
        return {'titel': url, 'lank': url, 'asking_price_opportunity': {
            'status': 'RESEARCH_SINGLE_ACTIVE', 'net_margin': margin, 'total_cost': 20, 'comparison_count': 1}}
    rows = positive_price_suggestions([
        row('https://www.tradera.com/item/1/123/card?q=a', 1),
        row('https://www.tradera.com/item/1/123/card?q=b', 1),
        row('https://www.tradera.com/item/1/456/card', 0.99),
        row('https://www.tradera.com/item/1/789/card', float('inf')),
        row('https://www.tradera.com/item/1/999/card', float('nan')),
    ])
    assert len(rows) == 1 and rows[0]['asking_price_opportunity']['net_margin'] == 1


def test_rendered_single_price_lead_precedes_smaller_profit_and_remains_marked_uncertain():
    from streamlit.testing.v1 import AppTest
    from src.asking_price_opportunity import build_asking_price_opportunity
    item = {'titel': '2023-24 Upper Deck #451 Connor Bedard', 'pris': 10, 'frakt': 22}
    def scenario(price, count):
        return build_asking_price_opportunity(item, {'rows': [
            dict(price=price, currency='SEK', url=f'https://www.ebay.com/itm/{i}', asking_comparison_eligible=True)
            for i in range(count)]})
    app = AppTest.from_string('''
import streamlit as st
from src.asking_price_ui import render_asking_price_shortlist
render_asking_price_shortlist(st.session_state['results'], research_leads=st.session_state['leads'])
''')
    app.session_state['results'] = [dict(item, titel='Two prices', lank='https://www.tradera.com/item/1/123/card',
                                         asking_price_opportunity=scenario(60, 2))]
    app.session_state['leads'] = [dict(title='One price', url='https://www.tradera.com/item/1/456/card', scenario=scenario(100, 1))]
    app.run()
    assert not app.exception
    text = '\n'.join(element.value for element in app.markdown)
    assert text.index('#### One price') < text.index('#### Two prices')
    assert 'Osäkert prisuppslag · endast 1 jämförelsepris' in text
    assert any('bara ett jämförelsepris' in element.label for element in app.expander)
    assert 'Ingen marginal' not in text


def test_hybrid_bid_is_conditional_even_when_legacy_sale_type_says_buy_now():
    from src.asking_price_opportunity import build_asking_price_opportunity
    item = {'titel': '2023-24 OPC Platinum #241 Arturs Silovs Pris: 20 kr, eller köp nu 50 kr',
            'pris': 20, 'frakt': 27, 'buyer_protection_fee': 3, 'sale_type': 'Köp nu'}
    result = build_asking_price_opportunity(item, {'rows': [
        dict(price=85, currency='SEK', url=str(i), asking_comparison_eligible=True) for i in range(2)]})
    assert result['auction_current_bid'] and result['total_cost'] == 50
    assert result['purchase_price'] == 20 and result['possible_find']


def test_restored_hybrid_scenario_displays_bid_condition_without_mutating_saved_evidence():
    from streamlit.testing.v1 import AppTest
    from src.asking_price_opportunity import build_asking_price_opportunity
    item = {'titel': '2023-24 OPC Platinum #241 Arturs Silovs Pris: 20 kr, eller köp nu 50 kr',
            'pris': 20, 'frakt': 27, 'lank': 'https://www.tradera.com/item/1/123/card'}
    scenario = build_asking_price_opportunity(item, {'rows': [
        dict(price=85, currency='SEK', url='https://www.ebay.com/itm/456', asking_comparison_eligible=True)]})
    scenario['auction_current_bid'] = False  # legacy saved result
    app = AppTest.from_string('''
import streamlit as st
from src.asking_price_ui import render_asking_price_shortlist
render_asking_price_shortlist(st.session_state['results'])
''')
    app.session_state['results'] = [dict(item, asking_price_opportunity=scenario)]
    app.run()
    assert not app.exception
    assert any('Auktion: nettovinsten gäller' in element.value for element in app.info)
    assert app.session_state['results'][0]['asking_price_opportunity']['auction_current_bid'] is False
