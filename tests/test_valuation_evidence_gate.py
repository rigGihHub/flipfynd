from src.valuation_evidence_gate import build_valuation_evidence_gate


def gate(**overrides):
    data = dict(
        comp_valuation_basis="sold",
        sold_comparable_count=2,
        valuation_confidence_score=70,
        exact_identity_gate={
            "status": "SÖKBAR",
            "supports_exact_comp_search": True,
            "supports_dynamic_max_bid": False,
        },
        premium_identity=False,
        premium_exact_sold_count=0,
    )
    data.update(overrides)
    return build_valuation_evidence_gate(**data)


def test_allows_market_value_with_existing_decision_grade_sold_and_identity():
    out = gate()
    assert out["market_value_safe"] is True
    assert out["max_purchase_safe"] is True


def test_blocks_heuristic_or_asking_value():
    assert gate(comp_valuation_basis="none")["market_value_safe"] is False
    assert gate(comp_valuation_basis="asking")["market_value_safe"] is False


def test_blocks_when_fewer_than_two_verified_sold_comps():
    out = gate(sold_comparable_count=1)
    assert out["market_value_safe"] is False
    assert any("minst två" in x for x in out["blockers"])


def test_blocks_when_identity_not_exact_search_ready():
    out = gate(exact_identity_gate={
        "status": "GRANSKA",
        "supports_exact_comp_search": False,
        "supports_dynamic_max_bid": False,
    })
    assert out["market_value_safe"] is False


def test_premium_still_requires_two_exact_premium_sales():
    assert gate(premium_identity=True, premium_exact_sold_count=1)["market_value_safe"] is False
    assert gate(premium_identity=True, premium_exact_sold_count=2)["market_value_safe"] is True


def test_dynamic_bid_permission_remains_stricter():
    assert gate()["dynamic_max_bid_safe"] is False
    assert gate(exact_identity_gate={
        "status": "VERIFIERAD",
        "supports_exact_comp_search": True,
        "supports_dynamic_max_bid": True,
    })["dynamic_max_bid_safe"] is True
