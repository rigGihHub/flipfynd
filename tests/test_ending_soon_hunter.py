from src.ending_soon_hunter import parse_remaining_minutes, build_ending_soon_opportunity


def base(**overrides):
    item = {
        "sale_type": "Auktion",
        "exact_end_text": "2 tim 15 min kvar",
        "total_cost": 600,
        "max_total_price": 800,
        "valuation_confidence_score": 78,
        "exact_identity_gate_score": 88,
        "exact_identity_gate_supports_dynamic_max_bid": True,
        "risk_score": 25,
        "sold_comparable_count": 3,
        "identity_conflicts": [],
        "is_lot": False,
    }
    item.update(overrides)
    return item


def test_parse_relative_swedish_time():
    assert parse_remaining_minutes("1 dag 2 tim 5 min") == 1565
    assert parse_remaining_minutes("45 minuter") == 45


def test_ambiguous_absolute_time_is_not_guessed():
    assert parse_remaining_minutes("2 sep 21:30") is None


def test_strong_ending_soon_candidate_is_eligible():
    out = build_ending_soon_opportunity(base())
    assert out["eligible"] is True
    assert out["remaining_minutes"] == 135
    assert out["safe_for_valuation"] is False


def test_over_max_bid_is_blocked():
    out = build_ending_soon_opportunity(base(total_cost=850))
    assert out["eligible"] is False
    assert any("över säkert maxbud" in x for x in out["blockers"])


def test_unknown_end_time_is_blocked():
    out = build_ending_soon_opportunity(base(exact_end_text="Ikväll"))
    assert out["eligible"] is False


def test_buy_now_is_not_eligible():
    out = build_ending_soon_opportunity(base(sale_type="Köp nu"))
    assert out["eligible"] is False
