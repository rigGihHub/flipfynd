from src.seller_top5_controller import resolve_seller_top5


def _fake_analyze(item, mode="fast", strategy_mode=None, sport=None, all_items=None):
    return {
        "titel": item.get("titel") or item.get("title") or "",
        "lank": item.get("lank") or item.get("url"),
        "pris": item.get("pris") or item.get("price") or 0,
        "exact_identity_gate_supports_exact_comp_search": True,
        "exact_identity_gate_score": 90,
        "valuation_confidence_score": 70,
        "market_edge_score": item.get("edge", 30),
        "sold_comparable_count": item.get("sold", 1),
        "rank_score": 70,
        "beslut": item.get("decision", "UNDERSÖK"),
    }


def test_uses_local_market_when_credentials_are_missing():
    local = [
        {"titel": "Local deal", "lank": "local", "pris": 50, "saljare": "Etanol71", "sold": 2, "decision": "KÖP"},
        {"titel": "Other", "lank": "other", "pris": 20, "saljare": "SomeoneElse"},
    ]

    out = resolve_seller_top5("Etanol71", local, analyze_fn=_fake_analyze, credentials=None)

    assert out["inventory_source"] == "LOCAL_MARKET"
    assert out["fallback_reason"] == "NO_API_CREDENTIALS"
    assert out["api_status"] == "NOT_CONFIGURED"
    assert out["local_seller_match_count"] == 1
    assert out["rows"][0]["title"] == "Local deal"


def test_live_api_wins_when_it_succeeds():
    def fetcher(**kwargs):
        return {
            "ok": True,
            "status": "OK",
            "items": [
                {"titel": "Live deal", "lank": "live", "pris": 80, "saljare": "Etanol71", "sold": 3, "decision": "KÖP"}
            ],
        }

    local = [{"titel": "Stale local", "lank": "local", "pris": 5, "saljare": "Etanol71", "sold": 5, "decision": "KÖP"}]
    out = resolve_seller_top5(
        "Etanol71",
        local,
        analyze_fn=_fake_analyze,
        credentials=("id", "key"),
        inventory_fetcher=fetcher,
    )

    assert out["inventory_source"] == "TRADERA_API"
    assert out["fallback_reason"] is None
    assert out["rows"][0]["title"] == "Live deal"


def test_api_failure_falls_back_to_local_market():
    def fetcher(**kwargs):
        return {"ok": False, "status": "HTTP_ERROR", "error": "boom", "items": []}

    local = [{"titel": "Local deal", "lank": "local", "pris": 50, "saljare": "Etanol71", "sold": 2}]
    out = resolve_seller_top5(
        "Etanol71",
        local,
        analyze_fn=_fake_analyze,
        credentials=("id", "key"),
        inventory_fetcher=fetcher,
    )

    assert out["inventory_source"] == "LOCAL_MARKET"
    assert out["fallback_reason"] == "API_FAILED"
    assert out["api_status"] == "HTTP_ERROR"
    assert out["rows"][0]["title"] == "Local deal"


def test_successful_empty_api_inventory_is_authoritative_not_replaced_by_stale_local_data():
    def fetcher(**kwargs):
        return {"ok": True, "status": "OK", "items": []}

    local = [{"titel": "Stale local", "lank": "local", "pris": 10, "saljare": "Etanol71", "sold": 2}]
    out = resolve_seller_top5(
        "Etanol71",
        local,
        analyze_fn=_fake_analyze,
        credentials=("id", "key"),
        inventory_fetcher=fetcher,
    )

    assert out["inventory_source"] == "TRADERA_API"
    assert out["status"] == "NO_ITEMS"
    assert out["inventory_count"] == 0
    assert out["rows"] == []


def test_fetch_exception_fails_closed_into_local_fallback():
    def fetcher(**kwargs):
        raise RuntimeError("network down")

    local = [{"titel": "Local deal", "lank": "local", "pris": 50, "saljare": "Etanol71", "sold": 1}]
    out = resolve_seller_top5(
        "Etanol71",
        local,
        analyze_fn=_fake_analyze,
        credentials=("id", "key"),
        inventory_fetcher=fetcher,
    )

    assert out["inventory_source"] == "LOCAL_MARKET"
    assert out["fallback_reason"] == "API_FAILED"
    assert out["api_status"] == "FETCH_EXCEPTION"


def test_missing_seller_is_explicit_and_does_not_call_api():
    called = {"value": False}

    def fetcher(**kwargs):
        called["value"] = True
        return {"ok": True, "items": []}

    out = resolve_seller_top5(
        " ",
        [],
        analyze_fn=_fake_analyze,
        credentials=("id", "key"),
        inventory_fetcher=fetcher,
    )

    assert out["status"] == "NO_SELLER"
    assert out["inventory_source"] == "NONE"
    assert called["value"] is False


def test_first_public_page_is_ranked_with_ordinary_engine_immediately(monkeypatch):
    calls = []
    monkeypatch.setattr("src.seller_top5_controller.load_checkpoint", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.seller_top5_controller.save_checkpoint", lambda *args, **kwargs: None)

    def public_fetcher(*args, **kwargs):
        return {
            "ok": True,
            "status": "OK",
            "seller": {"alias": "TestSeller"},
            "items": [
                {
                    "titel": "2023-24 Upper Deck Young Guns Rookie #201",
                    "lank": "https://www.tradera.com/item/293316/123456789/card",
                    "pris": 25,
                    "saljare": "TestSeller",
                    "seller_user_id": "987654321",
                    "tradera_item_id": "123456789",
                    "source_type": "tradera_public_seller_profile",
                    "sold": 2,
                }
            ],
            "pages_read": 1,
            "next_page": 2,
            "exhausted": False,
        }

    def analyze(item, **kwargs):
        calls.append(item["tradera_item_id"])
        return _fake_analyze(item, **kwargs)

    out = resolve_seller_top5(
        "",
        [],
        analyze_fn=analyze,
        credentials=None,
        profile_url="https://www.tradera.com/profile/items/987654321/TestSeller",
        public_fetcher=public_fetcher,
        public_pages=1,
    )

    assert out["status"] == "INVENTORY_PARTIAL"
    assert out["inventory_count"] == 1
    assert out["public_pages_read"] == 1
    assert out["public_next_page"] == 2
    assert out["ranking_source"] == "ORDINARY_FLIPFYND_RANK"
    assert out["rows"]
    assert calls


def test_transient_public_failure_retries_same_page_without_manual_resume(monkeypatch):
    calls = []
    monkeypatch.setattr("src.seller_top5_controller.load_checkpoint", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.seller_top5_controller.save_checkpoint", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.seller_top5_controller.clear_checkpoint", lambda *args, **kwargs: None)

    def public_fetcher(*args, **kwargs):
        calls.append(kwargs["start_page"])
        if len(calls) == 1:
            return {
                "ok": False,
                "status": "PROXY_TIMEOUT",
                "error": "Read timed out",
                "items": [],
                "next_page": kwargs["start_page"],
            }
        return {
            "ok": True,
            "status": "OK",
            "seller": {"alias": "TestSeller"},
            "items": [{
                "titel": "2023-24 Upper Deck Young Guns #201 Rookie",
                "lank": "https://www.tradera.com/item/293316/123456789/card",
                "pris": 25,
                "saljare": "TestSeller",
                "seller_user_id": "987654321",
                "tradera_item_id": "123456789",
                "source_type": "tradera_public_seller_profile",
                "sold": 2,
                "decision": "UNDERSÖK",
            }],
            "pages_read": 1,
            "next_page": 2,
            "exhausted": True,
        }

    out = resolve_seller_top5(
        "TestSeller", [], analyze_fn=_fake_analyze, credentials=None,
        profile_url="https://www.tradera.com/profile/items/987654321/TestSeller",
        public_fetcher=public_fetcher, public_pages=1,
    )

    assert calls == [1, 1]
    assert out["public_status"] == "OK"
    assert out["public_retry_count"] == 1
    assert out["inventory_count"] == 1
