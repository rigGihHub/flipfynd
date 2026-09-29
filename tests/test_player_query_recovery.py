from src.asking_price_opportunity import asking_research_identity


def test_set_and_world_cup_are_not_a_player():
    row = {'titel': '2004-05 Ultimate Collection World Cup of Hockey 203/299 Milan Hejduk #67 Sluttid Imorgon 20:57 . Pris: 28 kr'}
    identity = asking_research_identity(row)
    assert identity['player_name'] == 'Milan Hejduk'
    assert identity['card_number'] == '67'
    assert identity['serial_denominator'] == 299


def test_optional_search_timeout_preserves_primary_comparison(monkeypatch):
    import requests
    from src import asking_price_opportunity as module
    calls = []
    monkeypatch.setattr(module, 'configured_credentials', lambda: ('id', 'secret'))
    def fetch(query, identity):
        calls.append(query)
        if len(calls) == 2:
            raise requests.ConnectTimeout()
        return {'rows': [{'url': 'https://example.com/exact', 'price': 100,
                          'currency': 'SEK', 'asking_comparison_eligible': True}],
                'raw_listing_count': 1}
    monkeypatch.setattr(module, 'fetch_configured_ebay_active_context', fetch)
    row = {'titel': '2004-05 Ultimate Collection World Cup of Hockey 203/299 Milan Hejduk #67',
           'pris': 10, 'frakt': 20}
    result = module.attach_asking_price_opportunity(row)
    assert len(calls) == 2
    assert result['asking_price_opportunity']['status'] == 'RESEARCH_SINGLE_ACTIVE'
    assert result['asking_price_opportunity']['comparison_count'] == 1
    assert result['ebay_active_context']['expansion_error'] == 'ConnectTimeout'
