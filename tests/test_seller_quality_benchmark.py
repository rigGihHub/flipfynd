import json
from pathlib import Path

from src.seller_quality_benchmark import evaluate_seller_quality_portfolio


ROOT = Path(__file__).resolve().parents[1]


def _portfolio():
    payload = json.loads((ROOT / "data" / "seller_quality_benchmark.json").read_text(encoding="utf-8"))
    return payload["cases"]


def test_versioned_seller_quality_contract_passes_without_claiming_real_accuracy():
    result = evaluate_seller_quality_portfolio(_portfolio())
    assert result["schema_valid"] is True
    assert result["release_gate"] == "PASS"
    assert result["contract_precision_pct"] == 100.0
    assert result["contract_recall_pct"] == 100.0
    assert result["safety_specificity_pct"] == 100.0
    assert result["real_accuracy_measured"] is False
    assert result["real_precision_pct"] is None
    assert result["real_recall_pct"] is None
    assert result["product_validation_status"] == "COLLECTING_REAL_OUTCOMES"


def test_observed_zero_and_negative_margin_regressions_are_not_highlighted():
    result = evaluate_seller_quality_portfolio(_portfolio())
    observed = [row for row in result["results"] if row["source_kind"] == "observed_ui_regression"]
    assert len(observed) == 3
    assert all(row["predicted_find"] is False for row in observed)
    assert all(row["predicted_highlight"] is False for row in observed)


def test_bad_schema_and_duplicate_ids_fail_the_release_gate():
    cases = [
        {"id": "same", "source_kind": "synthetic_safety", "expected_find": False,
         "expected_highlight": False, "row": {}},
        {"id": "same", "source_kind": "invented_real_data", "expected_find": False,
         "expected_highlight": False, "row": {}},
    ]
    result = evaluate_seller_quality_portfolio(cases)
    assert result["schema_valid"] is False
    assert result["release_gate"] == "FAIL"
    assert any("duplicerat case-id" in error for error in result["schema_errors"])


def test_completed_trade_requires_explicit_outcome_verification():
    result = evaluate_seller_quality_portfolio([{
        "id": "unverified-trade",
        "source_kind": "completed_real_trade",
        "expected_find": True,
        "expected_highlight": True,
        "row": {},
    }])
    assert result["schema_valid"] is False
    assert result["real_accuracy_measured"] is True
    assert result["release_gate"] == "FAIL"
