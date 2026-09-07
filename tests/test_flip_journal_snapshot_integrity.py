from src.flip_journal import build_entry_from_listing, SCHEMA_VERSION

def test_schema_bumped():
    assert SCHEMA_VERSION == 6

def test_net_profit_estimate_is_captured_when_primary_missing():
    e=build_entry_from_listing({"titel":"x","net_profit_estimate":75}, purchase_price=100)
    assert e["expected_net_profit_at_capture"]==75
    assert e["expected_roi_pct_at_capture"]==75

def test_explicit_net_profit_has_precedence():
    e=build_entry_from_listing({"titel":"x","net_profit":60,"net_profit_estimate":75}, purchase_price=100)
    assert e["expected_net_profit_at_capture"]==60

def test_resale_aliases_are_explicit_only():
    e=build_entry_from_listing({"titel":"x","expected_resale":250})
    assert e["expected_resale_at_capture"]==250

def test_velocity_requires_verified_sold_evidence():
    e=build_entry_from_listing({"titel":"x","flip_velocity_expected_days":12,"flip_velocity_evidence":"heuristic"})
    assert e["flip_velocity_days_at_capture"] is None
    assert e["flip_velocity_evidence_at_capture"]=="heuristic"

def test_verified_velocity_is_captured():
    e=build_entry_from_listing({"titel":"x","flip_velocity_expected_days":12,"flip_velocity_evidence":"verified_sold_velocity"})
    assert e["flip_velocity_days_at_capture"]==12
    assert e["flip_velocity_evidence_at_capture"]=="verified_sold_velocity"

def test_prediction_timestamp_is_frozen_at_capture():
    e=build_entry_from_listing({"titel":"x"})
    assert e["prediction_timestamp_at_capture"]==e["created_at"]
