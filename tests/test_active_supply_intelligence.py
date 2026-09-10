from src.active_supply_intelligence import build_supply_query, verify_active_supply, classify_verified_supply

def test_query_requires_structured_player():
    assert build_supply_query("") is None
    assert build_supply_query(" Connor McDavid ")=="Connor McDavid"

def test_verify_fails_closed_without_supported_category():
    out=verify_active_supply({"player_name":"A"},app_id="1",app_key="k",category_name="Unknown")
    assert out["ok"] is False
    assert out["creates_buy_decision"] is False
    assert out["creates_value"] is False

def test_verified_supply_dedupes_across_pages(monkeypatch):
    def fake(**kwargs):
        page=kwargs["page_number"]
        items=[{"tradera_item_id":"1"}]
        if page==2: items.append({"tradera_item_id":"2"})
        return {"ok":True,"status":"OK","items":items}
    monkeypatch.setattr("src.active_supply_intelligence.search_once",fake)
    out=verify_active_supply({"player_name":"A"},app_id="1",app_key="k",category_name="Hockey - NHL",pages=2)
    assert out["observed_unique_items"]==2
    assert classify_verified_supply(out)=="FÅ_OBSERVERADE_TRÄFFAR"

def test_classification_is_descriptive_only():
    out={"ok":True,"observed_unique_items":7}
    assert classify_verified_supply(out)=="BEGRÄNSAT_OBSERVERAT_UTBUD"
