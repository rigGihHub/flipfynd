import src.decision_tiers_compat as compat
from src.decision_tiers_compat import build_decision_tiers_compat


def _good(title="Good"):
    return {
        "title": title,
        "decision": "KÖP",
        "sold_comparable_count": 2,
        "exact_identity_gate_supports_exact_comp_search": True,
        "valuation_display_safe": True,
        "market_value_estimate": 200,
        "analysis_total_cost": 100,
        "dynamic_max_total_price": 130,
    }


def _research_item(title="Research"):
    return {
        "title": title,
        "decision": "SKIP",
        "deal_score": 80,
        "sold_comparable_count": 0,
        "exact_identity_gate_supports_exact_comp_search": True,
        "exact_identity_gate_supports_comp_research": True,
        "exact_identity_gate_status": "READY",
        "exact_identity_gate_identity_fields": {
            "player_name": "Nathan MacKinnon",
            "set_name": "Upper Deck Series 1",
            "season": "2024-25",
            "card_number": "GFOV-12",
        },
    }


def test_current_signature_receives_gate():
    seen = {}
    def current(candidates, total_limit=3, require_verified_economic_edge=False):
        seen["gate"] = require_verified_economic_edge
        return {"rows": candidates[:total_limit]}
    out = build_decision_tiers_compat(current, [_good()], require_verified_economic_edge=True)
    assert seen["gate"] is True
    assert len(out["rows"]) == 1


def test_legacy_signature_is_prefiltered():
    def legacy(candidates, total_limit=3):
        return {"rows": candidates[:total_limit]}
    bad = _good("Bad")
    bad["sold_comparable_count"] = 0
    out = build_decision_tiers_compat(legacy, [bad, _good()], require_verified_economic_edge=True)
    assert [row["title"] for row in out["rows"]] == ["Good"]
    assert out["rejected_count"] == 1


def test_legacy_gate_rejects_cost_above_max():
    def legacy(candidates, total_limit=3):
        return {"rows": candidates[:total_limit]}
    bad = _good("Too expensive")
    bad["analysis_total_cost"] = 150
    out = build_decision_tiers_compat(legacy, [bad], require_verified_economic_edge=True)
    assert out["rows"] == []


def test_top3_preflight_attaches_low_guide_before_builder(monkeypatch):
    compat._cached_guide_lookup.cache_clear()
    monkeypatch.setenv("SPORTSCARDSPRO_TOKEN", "token")
    monkeypatch.setattr(
        compat,
        "fetch_sportscardspro_context",
        lambda identity, token=None: {
            "ok": True,
            "status": "CONTEXT_ONLY",
            "ungraded_usd": 1.50,
            "product_name": "MacKinnon insert",
        },
    )
    seen = {}
    def current(candidates, total_limit=3, require_verified_economic_edge=False):
        seen["row"] = candidates[0]
        return {"rows": candidates[:total_limit]}

    build_decision_tiers_compat(current, [_research_item()], require_verified_economic_edge=True)

    row = seen["row"]
    assert row["price_guide_auto_prefetched"] is True
    assert row["guide_triage"]["status"] == "LOW_GUIDE_CONTEXT"
    assert row["guide_triage"]["ungraded_usd"] == 1.5
    assert row["sports_cards_pro"]["ungraded_usd"] == 1.5


def test_preflight_never_queries_verified_two_sale_buy(monkeypatch):
    compat._cached_guide_lookup.cache_clear()
    monkeypatch.setenv("SPORTSCARDSPRO_TOKEN", "token")
    calls = []
    monkeypatch.setattr(
        compat,
        "fetch_sportscardspro_context",
        lambda identity, token=None: calls.append(identity) or {"ok": True, "ungraded_usd": 1.0},
    )
    def current(candidates, total_limit=3, require_verified_economic_edge=False):
        return {"rows": candidates[:total_limit]}

    out = build_decision_tiers_compat(current, [_good()], require_verified_economic_edge=True)

    assert len(out["rows"]) == 1
    assert calls == []


def test_preflight_is_inert_without_token(monkeypatch):
    compat._cached_guide_lookup.cache_clear()
    monkeypatch.delenv("SPORTSCARDSPRO_TOKEN", raising=False)
    calls = []
    monkeypatch.setattr(
        compat,
        "fetch_sportscardspro_context",
        lambda identity, token=None: calls.append(identity) or {"ok": True, "ungraded_usd": 1.0},
    )
    def current(candidates, total_limit=3, require_verified_economic_edge=False):
        return {"rows": candidates[:total_limit]}

    out = build_decision_tiers_compat(current, [_research_item()], require_verified_economic_edge=True)

    assert len(out["rows"]) == 1
    assert calls == []
    assert "guide_triage" not in out["rows"][0]
