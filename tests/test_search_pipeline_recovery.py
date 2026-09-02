from pathlib import Path

import src.tradera_fetcher as tf


def test_reconcile_repairs_obviously_stale_cross_sport_coverage(tmp_path, monkeypatch):
    state_path = tmp_path / 'state.json'
    monkeypatch.setattr(tf, 'STATE_PATH', state_path)
    tf.save_fetch_state({
        'categories': {
            'Hockey - NHL': {
                'loaded_pages': list(range(1, 126)),
                'market_next_page': 126,
                'market_complete': False,
                'page_loaded_at': {str(i): '2026-09-02T18:00:00+00:00' for i in range(1, 126)},
            }
        }
    })
    items = [
        {'lank': f'https://www.tradera.com/item/293316/{1000+i}/kort', 'sida': page, 'source_category': 'Hockey - NHL'}
        for i, page in enumerate([1, 1, 2, 3, 4])
    ]
    repaired = tf.reconcile_market_state_with_items(items)
    assert repaired == ['Hockey - NHL']
    info = tf.load_fetch_state()['categories']['Hockey - NHL']
    assert info['loaded_pages'] == [1, 2, 3, 4]
    assert info['market_next_page'] == 5
    assert info['market_complete'] is False


def test_reconcile_does_not_touch_plausible_deep_coverage(tmp_path, monkeypatch):
    state_path = tmp_path / 'state.json'
    monkeypatch.setattr(tf, 'STATE_PATH', state_path)
    tf.save_fetch_state({
        'categories': {
            'Fotboll': {
                'loaded_pages': list(range(1, 126)),
                'market_next_page': 126,
                'market_complete': False,
            }
        }
    })
    items = [
        {'lank': 'https://www.tradera.com/item/293311/12345/kort', 'sida': 100, 'source_category': 'Fotboll'}
    ]
    assert tf.reconcile_market_state_with_items(items) == []
    info = tf.load_fetch_state()['categories']['Fotboll']
    assert max(info['loaded_pages']) == 125
    assert info['market_next_page'] == 126
