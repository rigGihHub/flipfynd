import json
from src.tradera_api_search import (
    extract_search_rows,
    normalize_search_item,
    search_once,
    run_search_plan,
    save_expansion_items,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code=status_code
        self._payload=payload
    def json(self):
        return self._payload


def test_extract_rows_fails_closed_on_unknown_shape():
    assert extract_search_rows({"unexpected":[{"itemId":1}]}) == []


def test_normalizer_requires_explicit_id_and_title():
    assert normalize_search_item({"title":"X"},category_name="Fotboll",query="x",order_by="Relevance") is None
    assert normalize_search_item({"itemId":1},category_name="Fotboll",query="x",order_by="Relevance") is None


def test_normalizer_uses_only_explicit_api_fields():
    out=normalize_search_item(
        {"itemId":123,"title":"Card","price":50,"itemUrl":"https://example.invalid/item"},
        category_name="Hockey - NHL",query="Card",order_by="PriceAscending"
    )
    assert out["pris"] == 50.0
    assert out["frakt"] is None
    assert out["source_type"] == "tradera_api_search_expansion"
    assert out["search_expansion_candidate"] is True


def test_search_once_uses_app_headers_and_v4_params(monkeypatch):
    seen={}
    def fake_get(url,headers,params,timeout):
        seen.update(url=url,headers=headers,params=params)
        return FakeResponse(200,{"items":[{"itemId":7,"title":"Test","price":25}]})
    monkeypatch.setattr("src.tradera_api_search.requests.get",fake_get)
    out=search_once(app_id="1",app_key="k",query="Test",category_id=293316,
                    category_name="Hockey - NHL",order_by="EndDateAscending")
    assert out["ok"] is True
    assert out["parsed_count"] == 1
    assert seen["headers"]["X-App-Id"] == "1"
    assert seen["headers"]["X-App-Key"] == "k"
    assert seen["params"]["query"] == "Test"
    assert seen["params"]["categoryId"] == 293316


def test_run_plan_dedupes_same_item_across_search_routes(monkeypatch):
    def fake_search_once(**kwargs):
        return {"status":"OK","items":[{"tradera_item_id":"9","titel":"X"}]}
    monkeypatch.setattr("src.tradera_api_search.search_once",fake_search_once)
    plan={"searches":[
        {"query":"X","category_id":293316,"category_name":"Hockey - NHL","order_by":"Relevance","page_number":1},
        {"query":"X","category_id":293316,"category_name":"Hockey - NHL","order_by":"PriceAscending","page_number":1},
    ]}
    out=run_search_plan(plan,app_id="1",app_key="k")
    assert out["searches_run"] == 2
    assert out["unique_items"] == 1
    assert out["creates_buy_decision"] is False
    assert out["creates_value"] is False


def test_save_expansion_items_merges_by_tradera_id(tmp_path):
    path=tmp_path/"exp.json"
    assert save_expansion_items(path,[{"tradera_item_id":"1","titel":"A"}]) == 1
    assert save_expansion_items(path,[{"tradera_item_id":"1","titel":"A2"},{"tradera_item_id":"2","titel":"B"}]) == 2
    data=json.loads(path.read_text(encoding="utf-8"))
    assert {r["tradera_item_id"] for r in data} == {"1","2"}
