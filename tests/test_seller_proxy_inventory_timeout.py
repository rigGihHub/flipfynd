import requests
import pytest

from src.seller_proxy_inventory import _proxy_timeout


def test_proxy_timeout_has_cold_start_tolerant_default(monkeypatch):
    monkeypatch.delenv("FLIPFYND_SELLER_PROXY_TIMEOUT", raising=False)
    assert _proxy_timeout() == 60


def test_proxy_timeout_is_bounded_and_configurable(monkeypatch):
    monkeypatch.setenv("FLIPFYND_SELLER_PROXY_TIMEOUT", "90")
    assert _proxy_timeout() == 90
    monkeypatch.setenv("FLIPFYND_SELLER_PROXY_TIMEOUT", "999")
    assert _proxy_timeout() == 120
    monkeypatch.setenv("FLIPFYND_SELLER_PROXY_TIMEOUT", "1")
    assert _proxy_timeout() == 10


def test_timeout_error_is_distinguishable_from_other_request_failures():
    assert issubclass(requests.Timeout, requests.RequestException)


@pytest.mark.parametrize('configured,expected', [(None, 60), ('90', 90)])
def test_seller_round_uses_proxy_timeout_setting(monkeypatch, configured, expected):
    from src import seller_round_job, seller_proxy_inventory
    if configured is None:
        monkeypatch.delenv('FLIPFYND_SELLER_PROXY_TIMEOUT', raising=False)
    else:
        monkeypatch.setenv('FLIPFYND_SELLER_PROXY_TIMEOUT', configured)
    calls = []
    class Response:
        status_code = 200
        def json(self):
            return {'items': [], 'exhausted': True}
    def get(url, **kwargs):
        calls.append(kwargs['timeout'])
        return Response()
    monkeypatch.setattr(seller_proxy_inventory.requests, 'get', get)
    def start(token, params, work, **kwargs):
        work()
        return True
    monkeypatch.setattr(seller_round_job.resumable_search, 'start', start)
    def resolve(seller, items, **kwargs):
        return kwargs['public_fetcher'](kwargs['profile_url'])
    assert seller_round_job.start('test', seller='Cardland',
        profile_url='https://www.tradera.com/profile/items/6160765/',
        market_items=[], analyze_fn=lambda x: x, resolve_fn=resolve)
    assert calls == [expected]
