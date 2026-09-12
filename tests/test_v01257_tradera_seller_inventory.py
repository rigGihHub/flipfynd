from src.tradera_seller_inventory import (
    normalize_seller_item,
    resolve_seller_by_alias,
    fetch_active_seller_items,
    discover_active_seller_inventory,
)


class Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
    def json(self):
        return self._payload


def test_normalize_seller_item_prefers_bin_and_lowest_shipping():
    row = {
        "id": 123,
        "shortDescription": "1995-96 Pinnacle #101 Wayne Gretzky",
        "buyItNowPrice": 25,
        "nextBid": 10,
        "itemLink": "https://www.tradera.com/item/123",
        "shippingOptions": [{"cost": 39}, {"cost": 22}],
        "seller": {"id": 77, "alias": "Johan_9"},
    }
    item = normalize_seller_item(row)
    assert item["pris"] == 25
    assert item["frakt"] == 22
    assert item["saljare"] == "Johan_9"
    assert item["seller_user_id"] == 77
    assert item["source_type"] == "tradera_api_seller_inventory"


def test_resolve_seller_by_alias(monkeypatch):
    def fake_get(url, **kwargs):
        assert "/users/by-alias/Johan_9" in url
        return Resp({"id": 77, "alias": "Johan_9"})
    monkeypatch.setattr("src.tradera_seller_inventory.requests.get", fake_get)
    out = resolve_seller_by_alias("Johan_9", app_id="1", app_key="k")
    assert out["ok"] is True
    assert out["seller"] == {"id": 77, "alias": "Johan_9"}


def test_fetch_active_seller_items_uses_active_filter(monkeypatch):
    seen = {}
    def fake_get(url, **kwargs):
        seen.update(kwargs.get("params") or {})
        return Resp([
            {"id": 1, "shortDescription": "Card A", "nextBid": 10, "shippingOptions": [{"cost": 22}]},
            {"id": 2, "shortDescription": "Card B", "buyItNowPrice": 30, "shippingOptions": [{"cost": 22}]},
        ])
    monkeypatch.setattr("src.tradera_seller_inventory.requests.get", fake_get)
    out = fetch_active_seller_items(seller_id=77, seller_alias="Johan_9", app_id="1", app_key="k")
    assert out["ok"] is True
    assert seen["filterActive"] == 1
    assert len(out["items"]) == 2
    assert all(x["saljare"] == "Johan_9" for x in out["items"])


def test_discover_active_seller_inventory_chains_alias_and_items(monkeypatch):
    calls = []
    def fake_get(url, **kwargs):
        calls.append(url)
        if "/users/by-alias/" in url:
            return Resp({"id": 77, "alias": "Johan_9"})
        return Resp([{"id": 2, "shortDescription": "Card B", "buyItNowPrice": 30}])
    monkeypatch.setattr("src.tradera_seller_inventory.requests.get", fake_get)
    out = discover_active_seller_inventory(seller_alias="Johan_9", app_id="1", app_key="k")
    assert out["ok"] is True
    assert out["seller"]["id"] == 77
    assert len(out["items"]) == 1
    assert len(calls) == 2
