from src.analyzer import compute_flip_velocity


def test_velocity_requires_verified_sold_evidence():
    out = compute_flip_velocity({"evidence": "asking_only", "sold_90d": 0}, 80, 100, 200)
    assert out["score"] is None
    assert out["profit_30d"] is None
    assert out["label"] == "Ej bedömd"


def test_velocity_rewards_recent_verified_turnover():
    out = compute_flip_velocity({"evidence": "sold", "sold_30d": 4, "sold_90d": 6, "median_sold_age_days": 18}, 80, 120, 300)
    assert out["score"] >= 65
    assert out["expected_days"] <= 20
    assert out["profit_30d"] >= 120


def test_velocity_is_not_created_from_old_single_sale_as_fast():
    out = compute_flip_velocity({"evidence": "sold", "sold_30d": 0, "sold_90d": 1, "median_sold_age_days": 85}, 55, 100, 200)
    assert out["expected_days"] >= 60
