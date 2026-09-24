from src.normal_evidence_scenarios import build_normal_evidence_scenario_range


def sold(price, key, date="2026-09-01"):
    return {
        "price": price,
        "sold_comp_id": key,
        "date": date,
        "market_state": "sold",
    }


def test_normal_range_uses_only_verified_sold_marked_rows():
    rows = [
        sold(100, "1"),
        sold(120, "2"),
        sold(140, "3"),
        {"price": 999, "market_state": "asking"},
    ]
    result = build_normal_evidence_scenario_range(
        valuation_basis="sold",
        comparable_details=rows,
        total_cost=50,
        identity_verified=True,
    )
    assert result["available"] is True
    assert result["all_observed_prices"] == [100, 120, 140]
    assert result["evidence_type"] == "exact_sold"


def test_active_only_or_non_sold_basis_cannot_create_range():
    result = build_normal_evidence_scenario_range(
        valuation_basis="asking",
        comparable_details=[{"price": 500, "market_state": "asking"}],
        identity_verified=True,
    )
    assert result["available"] is False
    assert "SOLD" in result["note"]


def test_unverified_identity_blocks_even_strong_sold_set():
    result = build_normal_evidence_scenario_range(
        valuation_basis="sold",
        comparable_details=[sold(100, "1"), sold(120, "2"), sold(140, "3")],
        identity_verified=False,
    )
    assert result["status"] == "BLOCKED"
    assert result["available"] is False


def test_premium_range_uses_premium_exact_pool_not_broad_details():
    result = build_normal_evidence_scenario_range(
        valuation_basis="sold",
        comparable_details=[sold(100, "base-1"), sold(110, "base-2"), sold(120, "base-3")],
        premium_exact_comps=[sold(300, "premium-1"), sold(320, "premium-2"), sold(340, "premium-3")],
        premium_identity=True,
        identity_verified=True,
    )
    assert result["available"] is True
    assert result["all_observed_prices"] == [300, 320, 340]
    assert result["evidence_type"] == "exact_premium_sold"
