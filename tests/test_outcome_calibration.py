from src.flip_journal import build_entry_from_listing, update_entry
from src.outcome_calibration import build_outcome_calibration, sample_level


def sold_entry(i: int, *, decision="KÖP", info=False, profit=100, purchase=100, days=10):
    item = {
        "titel": f"Kort {i}",
        "lank": f"https://example.test/{i}",
        "beslut": decision,
        "net_profit": 80,
        "expected_resale_price": 220,
        "is_information_edge_candidate": info,
        "sport": "hockey",
    }
    row = build_entry_from_listing(item, purchase_price=purchase, purchase_date="2026-08-01")
    fee = 10
    package = 5
    sale_price = purchase + fee + package + profit
    return update_entry([row], row["id"], sale_date=f"2026-08-{1+days:02d}", sale_price=sale_price, selling_fee=fee, packaging_cost=package)[0]


def test_sample_gate_prevents_small_sample_claims():
    assert sample_level(4)["supports_description"] is False
    assert sample_level(5)["supports_description"] is True
    assert sample_level(9)["supports_tendency"] is False
    assert sample_level(10)["supports_tendency"] is True
    assert sample_level(20)["supports_adjustment_review"] is True


def test_calibration_uses_only_sold_outcomes():
    sold = sold_entry(1)
    open_row = build_entry_from_listing({"titel": "Öppen"}, purchase_price=50)
    report = build_outcome_calibration([sold, open_row])
    assert report["sold_count"] == 1
    assert report["overall"]["count"] == 1


def test_real_roi_is_computed_and_reported():
    rows = [sold_entry(i, profit=100, purchase=100) for i in range(1, 6)]
    report = build_outcome_calibration(rows)
    assert report["overall"]["median_roi_pct"] == 100.0
    assert report["overall"]["win_rate"] == 100.0


def test_signal_tendency_requires_ten_outcomes():
    rows = [sold_entry(i, info=True, profit=50+i) for i in range(1, 11)]
    report = build_outcome_calibration(rows)
    info = next(g for g in report["groups"] if g["key"] == "information_edge")
    assert info["count"] == 10
    assert info["sample"]["supports_tendency"] is True


def test_calibration_never_changes_weights_automatically():
    rows = [sold_entry(i, info=True) for i in range(1, 21)]
    report = build_outcome_calibration(rows)
    assert report["automatic_weight_changes"] is False
    info = next(g for g in report["groups"] if g["key"] == "information_edge")
    assert info["sample"]["supports_adjustment_review"] is True
