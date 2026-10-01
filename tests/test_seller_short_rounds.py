from src import seller_top5_controller as controller
from tests.test_seller_search_continuation import item, analyze


def test_large_inventory_analysis_is_bounded_and_resumable():
    inventory = [item(i) for i in range(4300)]
    calls = []

    def tracked(source, **kwargs):
        calls.append(kwargs.get('mode', 'fast'))
        return analyze(source, **kwargs)

    first = controller._rank('seller', inventory, analyze_fn=tracked,
                             quick_limit=60, full_limit=8, source='TEST',
                             progress_callback=lambda _: None)
    assert calls.count('fast') <= 80
    assert calls.count('full') <= 12
    assert 0 < first['full_unique_analysed'] <= 12
    assert first['pending_deep_analysis'] > 0
    calls.clear()
    second = controller._rank('seller', inventory, analyze_fn=tracked,
                              quick_limit=60, full_limit=8, source='TEST',
                              analysis_registry=first['analysis_registry'],
                              progress_callback=lambda _: None)
    assert calls.count('fast') <= 80
    assert calls.count('full') <= 12
    assert second['analysis_round'] == 2
    assert second['quick_unique_analysed'] > first['quick_unique_analysed']
    assert second['full_unique_analysed'] > first['full_unique_analysed']
    assert set(first['analysis_registry']['entries']) <= set(second['analysis_registry']['entries'])


def test_public_round_stops_after_three_pages_and_resumes_next_page(monkeypatch):
    monkeypatch.setattr(controller, 'load_checkpoint', lambda *a, **k: None)
    monkeypatch.setattr(controller, 'save_checkpoint', lambda *a, **k: None)
    pages = []

    def fetch(*args, **kwargs):
        page = kwargs['start_page']
        pages.append(page)
        return {'ok': True, 'status': 'OK', 'seller': {'alias': 'seller'},
                'items': [dict(item(i), saljare='seller', seller_user_id='6160765',
                               source_type='tradera_public_seller_profile')
                          for i in range(page * 80, (page + 1) * 80)],
                'pages_read': 1, 'next_page': page + 1, 'exhausted': False}

    kwargs = dict(analyze_fn=analyze, credentials=None,
                  profile_url='https://www.tradera.com/profile/items/6160765/seller',
                  public_fetcher=fetch, progress_callback=lambda _: None)
    first = controller.resolve_seller_top5('seller', [], **kwargs)
    assert pages == [1, 2, 3]
    assert first['inventory_count'] == 240
    assert first['public_next_page'] == 4
    second = controller.resolve_seller_top5('seller', [],
                                          resume_checkpoint=first['public_checkpoint'], **kwargs)
    assert pages == [1, 2, 3, 4, 5, 6]
    assert second['inventory_count'] == 480
    assert second['public_next_page'] == 7
    assert second['full_unique_analysed'] > first['full_unique_analysed']
