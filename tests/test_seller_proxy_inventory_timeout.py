import requests

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
