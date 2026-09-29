import requests
import pytest
from src import ebay_browse_context as browse
from src.asking_price_opportunity import attach_asking_price_opportunity, build_asking_price_opportunity
from src.price_research_session import price_research_run
from src.price_research_status import price_research_problem
from src.opportunity_top5 import build_opportunity_top5
from src.inventory_price_sweep import sweep_inventory

TITLE = "2023-24 Upper Deck #451 Connor Bedard"


def context(count=2):
    return {"rows": [{"price": 100, "currency": "SEK", "url": f"https://example.com/{i}",
                      "asking_comparison_eligible": True} for i in range(count)]}


@pytest.mark.parametrize("purchase,expected_margin,find", [(50.5, 1, True), (50.51, .99, False), (52, -.5, False)])
def test_one_krona_after_all_costs_is_enough(purchase, expected_margin, find):
    result = build_asking_price_opportunity({"titel": TITLE, "pris": purchase, "frakt": 22}, context())
    assert result["net_margin"] == expected_margin
    assert result["possible_find"] is find
    assert result["creates_sold_evidence"] is False


def test_top_five_orders_by_net_instead_of_gross_and_keeps_one_krona():
    def item(i, net, reference):
        return {"titel": TITLE, "lank": f"https://www.tradera.com/item/{i}", "analysis_total_cost": 60,
                "asking_price_opportunity": {"possible_find": True, "status": "POSSIBLE_FIND",
                    "comparison_count": 2, "reference_asking_price": reference, "net_margin": net}}
    rows = build_opportunity_top5([item(1, 1, 500), item(2, 40, 110)])["rows"]
    assert [row["asking_net_margin"] for row in rows] == [40, 1]
    assert [row["practical_margin"] for row in rows] == [40, 1]
    assert all(row["decision"] == "UNDERSÖK" for row in rows)


def test_first_429_prevents_remaining_browse_calls_and_honours_retry_after(monkeypatch):
    monkeypatch.setattr(browse, "_RATE_LIMITS", {})
    monkeypatch.setattr(browse, "_TOKEN_CACHE", {})
    clock = [100.0]
    monkeypatch.setattr(browse.time, "monotonic", lambda: clock[0])
    class Token:
        ok = True
        def json(self): return {"access_token": "test-token", "expires_in": 7200}
    calls = []
    response = requests.Response()
    response.status_code = 429
    response.headers["Retry-After"] = "120"
    monkeypatch.setattr(browse.requests, "post", lambda *a, **kw: Token())
    monkeypatch.setattr(browse.requests, "get", lambda *a, **kw: (calls.append(1) or response))
    for i in range(117):
        with pytest.raises(requests.HTTPError) as error:
            browse.fetch_ebay_active_context(str(i), client_id="quota-test", client_secret="secret")
        assert error.value.response.status_code == 429
    assert len(calls) == 1
    clock[0] += 121
    with pytest.raises(requests.HTTPError):
        browse.fetch_ebay_active_context("after pause", client_id="quota-test", client_secret="secret")
    assert len(calls) == 2


def test_run_deduplicates_requests_across_inventory_threads_without_cross_run_cache(monkeypatch):
    calls = []
    monkeypatch.setattr(browse, "configured_credentials", lambda: ("dedup", "secret"))
    monkeypatch.setattr(browse, "fetch_ebay_active_context", lambda *a, **kw: (calls.append(1) or context()))
    def enrich(row):
        result = browse.fetch_configured_ebay_active_context("same card", {"card_number": "451"})
        result["rows"].clear()  # A consumer must not mutate another listing's context.
        return row
    @price_research_run
    def work():
        sweep_inventory([{"id": str(i)} for i in range(20)], [], enrich)
        return browse.fetch_configured_ebay_active_context("same card", {"card_number": "451"})
    assert len(work()["rows"]) == 2
    assert calls == [1]
    work()
    assert calls == [1, 1]


def test_dedup_does_not_mix_base_and_autograph_evidence(monkeypatch):
    calls = []
    monkeypatch.setattr(browse, "configured_credentials", lambda: ("traits", "secret"))
    monkeypatch.setattr(browse, "fetch_ebay_active_context", lambda *a, **kw: (calls.append(kw["identity"]) or context()))
    @price_research_run
    def work():
        for auto in [False, True]:
            browse.fetch_configured_ebay_active_context("same query", {"is_auto": auto})
    work()
    assert len(calls) == 2


def test_api_stop_does_not_start_another_inventory_batch():
    rows, debug = sweep_inventory([{"id": "unchecked"}],
        [{"id": "failed", "asking_price_opportunity": {"http_status": 429}}],
        lambda row: pytest.fail("No additional lookup allowed"))
    assert rows == []
    assert debug["inventory_price_remaining"] == 1
    assert debug["inventory_price_stop"] == "API_LIMIT"


def test_old_saved_429_results_are_not_reported_as_no_finds():
    message = price_research_problem({"price_research_status_counts": {
        "COMPARISON_HTTP_ERROR/BROWSE/HTTP_429/HTTPError": 117}})
    assert "betyder inte att fynd saknas" in message
    assert price_research_problem({"price_research_status_counts": {"NO_MARGIN": 75}}) is None


def test_empty_primary_search_does_not_consume_a_second_query(monkeypatch):
    from src import asking_price_opportunity as module
    calls = []
    monkeypatch.setattr(module, "configured_credentials", lambda: ("id", "secret"))
    monkeypatch.setattr(module, "fetch_configured_ebay_active_context",
        lambda *a: (calls.append(1) or {"rows": [], "raw_listing_count": 0}))
    attach_asking_price_opportunity({"titel": TITLE, "pris": 10, "frakt": 22})
    assert calls == [1]


def test_api_error_cache_is_never_reused(monkeypatch):
    from src import analysis_cache as cache
    monkeypatch.setattr(cache, "_load_cache_payload", lambda: {"entries": {"test": {"result": {
        "asking_price_opportunity": {"status": "COMPARISON_HTTP_ERROR", "http_status": 429}}}}})
    assert cache.get_cached_analysis("test") is None


def test_pipeline_keeps_searching_for_better_find_after_first_positive(monkeypatch):
    from src import ordinary_analysis_pipeline_v2 as pipeline
    rows = [{"id": str(i), "titel": TITLE, "pris": 10, "frakt": 22,
             "source_category": "Hockey - NHL"} for i in range(200)]
    calls = []
    monkeypatch.setattr(pipeline, "analyze_item", lambda row, **kw: {
        **row, "confidence": 80, "rank_score": 80, "analysis_total_cost": 32, "beslut": "UNDERSÖK"})
    monkeypatch.setattr(pipeline, "get_cached_analysis", lambda signature: None)
    monkeypatch.setattr(pipeline, "set_cached_analysis", lambda *args: None)
    monkeypatch.setattr(pipeline, "configured_credentials", lambda: ("id", "secret"))
    monkeypatch.setattr("src.asking_price_opportunity.configured_credentials", lambda: ("id", "secret"))
    monkeypatch.setattr(pipeline, "attach_asking_price_opportunity", lambda row: {
        **row, "asking_price_opportunity": {"status": "POSSIBLE_FIND", "possible_find": True,
                    "net_margin": 1, "comparison_count": 2, "reference_asking_price": 40}})
    monkeypatch.setattr(pipeline, "sweep_inventory", lambda *args: (calls.append(1) or ([], {})))
    _, debug = pipeline.analyze_data(rows, "hockey", "", 1000, "Alla", 1, "standard", False, False, False)
    assert debug["price_research_funnel"]["possible_find"] > 0
    assert calls == [1]
