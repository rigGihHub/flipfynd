from src.shipping_truth import resolve_shipping
from src.best_buy_decision_card import build_best_buy_decision_card


def test_actual_shipping_beats_assumption():
    out = resolve_shipping({"frakt": 49, "max_price_shipping_assumption": 29})
    assert out["shipping"] == 49
    assert out["known"] is True
    assert out["label"] == "Frakt"


def test_zero_shipping_is_known_free_shipping():
    out = resolve_shipping({"frakt": 0, "max_price_shipping_assumption": 29})
    assert out["shipping"] == 0
    assert out["known"] is True
    assert out["source"] == "listing"


def test_missing_shipping_uses_assumption_and_marks_unknown():
    out = resolve_shipping({"max_price_shipping_assumption": 29})
    assert out["shipping"] == 29
    assert out["known"] is False
    assert out["label"] == "Antagen frakt"


def test_missing_everything_uses_default_assumption():
    out = resolve_shipping({})
    assert out["shipping"] == 29
    assert out["known"] is False


def _eligible_buy(**extra):
    row = {
        "titel": "Testkort",
        "decision": "KÖP",
        "analysis_total_cost": 120,
        "net_profit_estimate": 50,
        "floor_profit_estimate": 10,
        "expected_resale": 200,
        "max_total_price": 150,
        "max_item_price": 121,
        "exact_identity_gate_supports_dynamic_max_bid": True,
        "capital_efficiency": {"score": 75, "profit_30d": 20},
    }
    row.update(extra)
    return row


def test_best_buy_prefers_actual_shipping_over_assumption():
    out = build_best_buy_decision_card([
        _eligible_buy(frakt=45, max_price_shipping_assumption=29)
    ])
    card = out["card"]
    assert card["shipping"] == 45
    assert card["shipping_known"] is True
    assert card["shipping_label"] == "Frakt"


def test_best_buy_preserves_free_shipping_zero():
    out = build_best_buy_decision_card([
        _eligible_buy(frakt=0, max_price_shipping_assumption=29)
    ])
    card = out["card"]
    assert card["shipping"] == 0
    assert card["shipping_known"] is True


def test_best_buy_marks_assumed_shipping():
    out = build_best_buy_decision_card([
        _eligible_buy(max_price_shipping_assumption=29)
    ])
    card = out["card"]
    assert card["shipping"] == 29
    assert card["shipping_known"] is False
    assert card["shipping_label"] == "Antagen frakt"
