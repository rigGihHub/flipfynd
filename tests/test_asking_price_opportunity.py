from datetime import date

import pytest

from src.asking_price_opportunity import (
    attach_asking_price_opportunity, build_asking_price_opportunity,
    parse_ecb_rates, select_asking_price_research,
)
from src.ebay_browse_context import fetch_ebay_active_context
from src.seller_top5 import seller_result_tier, _seller_opportunity_rank_key

TITLE = "2023-24 Upper Deck #451 Connor Bedard"
IDENTITY = {"player_name": "Connor Bedard", "season": "2023-24", "set_name": "Upper Deck", "card_number": "451"}
ITEM = {"titel": TITLE, "pris": 10, "frakt": 22, "lank": "https://www.tradera.com/item/2933/123456789"}


def _context(price=50, **updates):
    row = {"price": price, "currency": "SEK", "url": "https://www.ebay.com/itm/123", "title": TITLE,
           "asking_comparison_eligible": True}
    row.update(updates)
    return {"rows": [row]}


def test_small_profitable_card_is_a_possible_find_without_sold():
    out = build_asking_price_opportunity(ITEM, _context())
    assert out["possible_find"]
    assert out["total_cost"] == 32
    assert out["selling_fee"] == 5
    assert out["packaging"] == 3
    assert out["net_margin"] == 10
    assert not out["creates_sold_evidence"]


@pytest.mark.parametrize("price", [1, 30, 38])
def test_nonpositive_margin_is_not_a_possible_find(price):
    assert not build_asking_price_opportunity(ITEM, _context(price))["possible_find"]


def test_cheapest_listing_controls_margin_not_expensive_outlier():
    context = _context(30)
    context["rows"] += _context(500, url="https://www.ebay.com/itm/456")["rows"]
    out = build_asking_price_opportunity(ITEM, context)
    assert out["reference_asking_price"] == 30
    assert not out["possible_find"]


def test_duplicates_do_not_inflate_evidence_count():
    context = _context()
    context["rows"] *= 3
    assert build_asking_price_opportunity(ITEM, context)["comparison_count"] == 1


def test_unknown_shipping_is_charged_and_labeled():
    out = build_asking_price_opportunity({**ITEM, "frakt": None}, _context())
    assert out["shipping"] == 29
    assert not out["shipping_known"]
    assert out["net_margin"] == 3


def test_free_shipping_is_preserved():
    out = build_asking_price_opportunity({**ITEM, "frakt": 0}, _context())
    assert out["shipping"] == 0
    assert out["shipping_known"]


def test_foreign_currency_requires_real_fx():
    assert not build_asking_price_opportunity(ITEM, _context(5, currency="USD"))["possible_find"]
    out = build_asking_price_opportunity(ITEM, _context(5, currency="USD"), fx={"date": "2026-09-16", "rates_to_sek": {"USD": 10}})
    assert out["reference_asking_price"] == 50
    assert out["net_margin"] == 10


@pytest.mark.parametrize("price", [float("nan"), float("inf"), -1, True, "oops"])
def test_invalid_prices_cannot_manufacture_margin(price):
    assert not build_asking_price_opportunity(ITEM, _context(price))["possible_find"]


@pytest.mark.parametrize("suffix", [" reprint", " digital card", " lot of 5", " damaged"])
def test_noncomparable_target_requires_review(suffix):
    assert not build_asking_price_opportunity({**ITEM, "titel": TITLE + suffix}, _context())["possible_find"]


class Response:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): pass
    def json(self): return self.payload


class Session:
    def __init__(self, title=TITLE, options=None):
        self.title = title
        self.options = options if options is not None else ["FIXED_PRICE"]
    def post(self, *args, **kwargs): return Response({"access_token": "test"})
    def get(self, *args, **kwargs):
        assert kwargs["params"]["filter"] == "buyingOptions:{FIXED_PRICE}"
        return Response({"itemSummaries": [{"title": self.title, "price": {"value": "50", "currency": "SEK"},
            "buyingOptions": self.options, "itemWebUrl": "https://www.ebay.com/itm/123"}]})


@pytest.mark.parametrize("suffix", ["", " PSA 10", " PSA Authentic", " Auto", " /50", " reprint", " lot of 5"])
def test_api_prices_require_matching_card_without_extra_premium_traits(suffix):
    context = fetch_ebay_active_context(TITLE, identity=IDENTITY, client_id="id", client_secret="secret", session=Session(TITLE + suffix))
    out = build_asking_price_opportunity(ITEM, context)
    assert out["possible_find"] is (suffix == "")


@pytest.mark.parametrize("options", [[], ["AUCTION"]])
def test_current_bids_are_not_asking_resale_prices(options):
    context = fetch_ebay_active_context(TITLE, identity=IDENTITY, client_id="id", client_secret="secret", session=Session(options=options))
    assert not build_asking_price_opportunity(ITEM, context)["possible_find"]


def test_ecb_cross_rate_and_stale_rate_rejection():
    xml = '<Envelope><Cube time="2026-09-15"><Cube currency="USD" rate="1.25"/><Cube currency="SEK" rate="12.5"/></Cube></Envelope>'
    out = parse_ecb_rates(xml, today=date(2026, 9, 16))
    assert out["rates_to_sek"]["USD"] == 10
    with pytest.raises(ValueError):
        parse_ecb_rates(xml, today=date(2026, 9, 30))


def test_sold_and_buy_fields_are_unchanged(monkeypatch):
    monkeypatch.setattr("src.asking_price_opportunity.configured_credentials", lambda: ("id", "secret"))
    monkeypatch.setattr("src.asking_price_opportunity.fetch_configured_ebay_active_context", lambda *a: _context())
    original = {**ITEM, "beslut": "SKIP", "sold_comparable_count": 0, "marknadsvarde": None}
    out = attach_asking_price_opportunity(original)
    assert out["asking_price_opportunity"]["possible_find"]
    for key in ("beslut", "sold_comparable_count", "marknadsvarde"):
        assert out[key] == original[key]
    assert "asking_price_opportunity" not in original
    assert seller_result_tier({**out, "decision": "SKIP"}) == "RESEARCH"


def test_economic_comparison_outranks_collector_signal_without_margin():
    possible = {"decision": "SKIP", "asking_price_opportunity": build_asking_price_opportunity(ITEM, _context())}
    collector = {"decision": "UNDERSÖK", "rank_score": 99, "collector_signal_score": 40}
    assert _seller_opportunity_rank_key(possible) > _seller_opportunity_rank_key(collector)


def test_cheap_base_cards_receive_research_slots_without_sold(monkeypatch):
    monkeypatch.setattr("src.asking_price_opportunity.configured_credentials", lambda: ("id", "secret"))
    rows = [{"source_item": {**ITEM, "pris": price}} for price in (100, 10, 50)]
    selected = select_asking_price_research(rows, limit=2)
    assert [r["source_item"]["pris"] for r in selected] == [10, 50]
    assert all(r["seller_deep_route"] == "ASKING_PRICE_RESEARCH" for r in selected)


def test_missing_credentials_does_not_start_requests(monkeypatch):
    monkeypatch.setattr("src.asking_price_opportunity.configured_credentials", lambda: ("", ""))
    monkeypatch.setattr("src.asking_price_opportunity.fetch_configured_ebay_active_context", lambda *a: pytest.fail("unexpected network"))
    assert attach_asking_price_opportunity(ITEM) == ITEM
    assert select_asking_price_research([{"source_item": ITEM}]) == []


def test_seller_pipeline_keeps_base_card_with_asking_margin(monkeypatch):
    from src.seller_top5 import build_seller_top5
    monkeypatch.setattr("src.asking_price_opportunity.configured_credentials", lambda: ("id", "secret"))
    monkeypatch.setattr("src.seller_live_full_analysis.configured_credentials", lambda: ("", ""))
    def analyze(item, mode="fast", **kwargs):
        out = {"beslut": "SKIP", "sold_comparable_count": 0, "rank_score": 0}
        if mode == "full":
            out["asking_price_opportunity"] = build_asking_price_opportunity(item, _context())
        return out
    result = build_seller_top5("seller", [ITEM], analyze_fn=analyze)
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["seller_deep_route"] == "ASKING_PRICE_RESEARCH"
    assert row["asking_price_opportunity"]["net_margin"] == 10
    assert row["label"] == "MÖJLIGT FYND · BEGÄRDA PRISER"
    assert row["sold_comps"] == 0


def test_full_analyzer_attaches_comparison_but_fast_does_not(monkeypatch):
    import src.analyzer as analyzer
    monkeypatch.setattr(analyzer, "analyze_core", lambda *a, **k: {"beslut": "SKIP"})
    monkeypatch.setattr("src.asking_price_opportunity.configured_credentials", lambda: ("id", "secret"))
    monkeypatch.setattr("src.asking_price_opportunity.fetch_configured_ebay_active_context", lambda *a: _context())
    assert analyzer.analyze_item_full(ITEM)["asking_price_opportunity"]["possible_find"]
    assert "asking_price_opportunity" not in analyzer.analyze_item_fast(ITEM)


def test_browse_token_is_reused_between_queries(monkeypatch):
    import src.ebay_browse_context as browse
    calls = []
    monkeypatch.setattr(browse, "_TOKEN_CACHE", {})
    monkeypatch.setattr(browse.requests, "post", lambda *a, **kw: (calls.append("token") or Response({"access_token": "test", "expires_in": 7200})))
    monkeypatch.setattr(browse.requests, "get", lambda *a, **kw: Response({"itemSummaries": []}))
    for query in ("card one", "card two"):
        browse.fetch_ebay_active_context(query, client_id="id", client_secret="test-secret")
    assert calls == ["token"]


def test_active_comparison_cache_expires(monkeypatch):
    import src.analysis_cache as cache
    result = {"ebay_active_context": {"fetched_at": "2020-01-01T00:00:00+00:00"}}
    monkeypatch.setattr(cache, "_load_cache_payload", lambda: {"entries": {"test": {"result": result}}})
    assert cache.get_cached_analysis("test") is None


def test_whole_search_cache_also_expires_active_comparisons():
    from src.search_run_cache import get_reusable_search, store_reusable_search
    results = [{"ebay_active_context": {"fetched_at": "2020-01-01T00:00:00+00:00"}}]
    cache = store_reusable_search("test", results, {})
    assert get_reusable_search(cache, "test") is None


def test_card_number_in_grade_cannot_overwrite_actual_card_number():
    target = {**IDENTITY, "card_number": "10", "grading_company": "PSA", "grade": "PSA 10"}
    context = fetch_ebay_active_context(TITLE, identity=target, client_id="id", client_secret="secret", session=Session(TITLE + " PSA 10"))
    assert not any(row["asking_comparison_eligible"] for row in context["rows"])


def test_ordinary_shortlist_renders_margin_and_listing_links():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_string('''
import streamlit as st
from src.asking_price_ui import render_asking_price_shortlist
render_asking_price_shortlist(st.session_state["results"])
''')
    app.session_state["results"] = [{**ITEM, "asking_price_opportunity": build_asking_price_opportunity(ITEM, _context())}]
    app.run()
    assert not app.exception
    text = "\n".join(element.value for element in app.markdown)
    assert "Möjliga fynd mot begärda priser" in text
    assert "Möjlig nettovinst +10 kr" in text
    assert "32 kr totalt" in text
    assert len(app.get("link_button")) == 2


def test_single_expensive_active_listing_is_research_signal_not_find():
    out = build_asking_price_opportunity(ITEM, _context(500))
    assert out["net_margin"] > 0
    assert out["research_signal"]
    assert out["weak_find_signal"]
    assert not out["possible_find"]
    assert out["status"] == "RESEARCH_SINGLE_ACTIVE"


def test_two_exact_active_prices_can_support_possible_find():
    context = _context(80)
    context["rows"] += _context(90, url="https://www.ebay.com/itm/456")["rows"]
    out = build_asking_price_opportunity(ITEM, context)
    assert out["comparison_count"] == 2
    assert out["evidence_sufficient_for_possible_find"]
    assert out["possible_find"]
