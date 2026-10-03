import time

from src.asking_price_ui import practical_price_suggestions, meaningful_opportunity_candidates
from src.asking_price_opportunity import build_asking_price_opportunity, attach_asking_price_opportunity
from src.ebay_browse_context import match_active_rows
from src.inventory_price_sweep import sweep_inventory
from src.price_research_checkpoint import extend_checkpoint, fresh_checkpoint, listing_fingerprint

TITLE = '2023-24 Upper Deck #451 Connor Bedard'


def context(price=100):
    return {'rows': [dict(price=price, currency='SEK', url=f'https://www.ebay.com/itm/{n}',
                         asking_comparison_eligible=True) for n in range(2)]}


def test_meaningful_profit_requires_both_35_kr_and_15_percent():
    def row(n, net, cost):
        return dict(titel=n, lank=n, asking_price_opportunity={
            'status': 'POSSIBLE_FIND', 'possible_find': True,
            'net_margin': net, 'total_cost': cost, 'comparison_count': 2})
    rows = [row('2 kr', 2.18, 92), row('34.99 kr', 34.99, 50),
            row('low return', 40, 400), row('boundary', 35, 100), row('strong', 80, 120)]
    assert [row['titel'] for row in practical_price_suggestions(rows)] == ['strong', 'boundary']
    assert [row['titel'] for row in meaningful_opportunity_candidates(rows)] == ['boundary', 'strong']
    assert meaningful_opportunity_candidates([{'titel': 'unknown'}, {'titel': 'verified', 'beslut': 'KÖP',
        'asking_price_opportunity': {'net_margin': 2}}]) == [
        {'titel': 'unknown'}, {'titel': 'verified', 'beslut': 'KÖP', 'asking_price_opportunity': {'net_margin': 2}}]


def test_2300_listing_search_resumes_to_a_late_meaningful_find():
    rows = [dict(id=str(n), titel=TITLE, pris=20 if n == 2001 else 200, frakt=22)
            for n in range(2300)]
    routes = [{'source_item': row} for row in rows]
    calls = []
    def enrich(row):
        calls.append(row['id'])
        return dict(row, asking_price_opportunity=build_asking_price_opportunity(row, context(150)))
    completed = {}
    for round_number in range(3):
        results, debug = sweep_inventory(routes, [], enrich, completed=completed.get('completed', []))
        completed = extend_checkpoint(routes, results, completed)
        if round_number < 2:
            assert not practical_price_suggestions(results)
            assert debug['inventory_price_remaining'] > 0
        else:
            found = practical_price_suggestions(results)
            assert [row['id'] for row in found] == ['2001']
            assert found[0]['asking_price_opportunity']['net_margin'] == 69.75
            assert debug['inventory_price_remaining'] == 0
    assert len(calls) == len(set(calls)) == 2300
    assert '2001' not in calls[:2000]
    assert not found[0]['asking_price_opportunity']['creates_sold_evidence']


def test_checkpoint_rechecks_price_changes_profitable_signals_errors_and_missing_fx():
    rows = [dict(id=str(n), titel=TITLE, pris=200, frakt=22) for n in range(5)]
    results = [dict(rows[0], asking_price_opportunity={'status': 'NO_MARGIN'}),
        dict(rows[1], asking_price_opportunity={'status': 'POSSIBLE_FIND', 'possible_find': True}),
        dict(rows[2], asking_price_opportunity={'status': 'RESEARCH_SINGLE_ACTIVE', 'research_signal': True}),
        dict(rows[3], asking_price_opportunity={'status': 'COMPARISON_HTTP_ERROR', 'http_status': 429}),
        dict(rows[4], asking_price_opportunity={'status': 'NO_MATCHED_PRICES_OR_FX',
                                             'comparison_failure_reason': 'NO_CONVERTIBLE_PRICE_OR_FX'})]
    checkpoint = extend_checkpoint(rows, results)
    assert checkpoint['completed'] == [listing_fingerprint(rows[0])]
    assert listing_fingerprint(dict(rows[0], pris=10)) not in checkpoint['completed']
    assert fresh_checkpoint(dict(checkpoint, created_at=time.time() - 3601)) == {}
    assert fresh_checkpoint(dict(checkpoint, created_at=time.time() + 2)) == {}
    assert 'rows' not in checkpoint and 'comparisons' not in checkpoint


def test_broader_query_recovers_exact_prices_without_using_wrong_variant_or_season(monkeypatch):
    from src import asking_price_opportunity as module
    monkeypatch.setattr(module, 'configured_credentials', lambda: ('id', 'secret'))
    calls = []
    def fetch(query, identity):
        calls.append(query)
        raw = [] if len(calls) == 1 else [
            dict(title=TITLE, price=150, currency='SEK', url='https://www.ebay.com/itm/1', buying_options=['FIXED_PRICE']),
            dict(title=TITLE, price=160, currency='SEK', url='https://www.ebay.com/itm/2', buying_options=['FIXED_PRICE']),
            dict(title=TITLE + ' Gold /50', price=1000, currency='SEK', url='https://www.ebay.com/itm/3', buying_options=['FIXED_PRICE']),
            dict(title=TITLE.replace('2023-24', '2024-25'), price=1500, currency='SEK', url='https://www.ebay.com/itm/4', buying_options=['FIXED_PRICE'])]
        return {'rows': match_active_rows(raw, identity), 'raw_listing_count': len(raw)}
    monkeypatch.setattr(module, 'fetch_configured_ebay_active_context', fetch)
    result = attach_asking_price_opportunity(dict(titel=TITLE, pris=20, frakt=22, beslut='SKIP', sold_comparable_count=0))
    scenario = result['asking_price_opportunity']
    assert len(calls) == 2 and calls[-1] == 'Connor Bedard #451'
    assert scenario['comparison_count'] == 2 and scenario['net_margin'] == 69.75
    assert result['beslut'] == 'SKIP' and result['sold_comparable_count'] == 0
    assert not scenario['creates_sold_evidence']


def test_description_continuation_advances_even_when_valid_details_lack_a_number():
    from src import description_price_identity as recovery
    recovery._DETAIL_CACHE.clear()
    rows = [dict(titel='Patrik Elias Silver Script MVP 08-09', pris=10,
                 lank=f'https://www.tradera.com/item/293316/{n}/card') for n in range(3)]
    def verifier(row):
        return dict(row, purchase_detail_verified=True, full_description='Kortet på bilden.')
    first = recovery.enrich_description_routes(rows, limit=2, verifier=verifier)
    second = recovery.enrich_description_routes(rows, limit=2, verifier=verifier,
        previously_checked=first['description_checked_fingerprints'])
    assert first['description_identity_checked'] == 2
    assert second['description_identity_checked'] == 1
    assert second['description_identity_remaining'] == 0
    assert second['description_identity_recovered'] == 0
    recovery._DETAIL_CACHE.clear()


def test_continued_pipeline_rechecks_cached_positive_without_mutating_cpu_cache(monkeypatch):
    from src import ordinary_analysis_pipeline_v2 as pipeline
    row = dict(id='cached-positive', titel=TITLE, pris=20, frakt=22, source_category='Hockey - NHL')
    cached = dict(row, purchase_cost_verified=True, confidence=.8, rank_score=80, beslut='UNDERSÖK',
                  asking_price_opportunity=build_asking_price_opportunity(row, context(150)))
    calls = []
    monkeypatch.setattr(pipeline, 'configured_credentials', lambda: ('id', 'secret'))
    monkeypatch.setattr('src.asking_price_opportunity.configured_credentials', lambda: ('id', 'secret'))
    monkeypatch.setattr('src.ebay_browse_context.fetch_configured_quota', lambda: {})
    monkeypatch.setattr(pipeline, 'analyze_item', lambda item, **kwargs: dict(item, confidence=.8, rank_score=80, beslut='UNDERSÖK'))
    monkeypatch.setattr(pipeline, 'get_cached_analysis', lambda signature: cached)
    monkeypatch.setattr(pipeline, 'attach_asking_price_opportunity', lambda item: (calls.append(item) or dict(item)))
    monkeypatch.setattr(pipeline, 'sweep_inventory', lambda *args, **kwargs: ([], {}))
    pipeline.analyze_data([row], 'hockey', '', 1000, 'Alla', 1, 'standard', False, False, False,
                         research_checkpoint={'updated_at': time.time(), 'completed': []})
    assert calls and all(not item['purchase_cost_verified'] for item in calls)
    assert cached['purchase_cost_verified'] is True
