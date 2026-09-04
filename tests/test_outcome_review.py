from src.outcome_review import (
    OUTCOME_REVIEW_REASONS,
    build_outcome_review_patch,
    normalize_review_reasons,
    reason_labels,
)


def test_review_keeps_only_known_unique_reasons_in_stable_order():
    values = ["variant_wrong", "unknown", "identity_wrong", "variant_wrong"]
    assert normalize_review_reasons(values) == ["identity_wrong", "variant_wrong"]


def test_review_patch_is_explicit_and_can_be_cleared():
    patch = build_outcome_review_patch(["condition_worse"], "Corner damage seen on arrival")
    assert patch["outcome_review_reasons"] == ["condition_worse"]
    assert patch["outcome_review_note"] == "Corner damage seen on arrival"
    assert patch["outcome_reviewed_at"]
    cleared = build_outcome_review_patch([], "")
    assert cleared["outcome_review_reasons"] == []
    assert cleared["outcome_reviewed_at"] is None


def test_reason_labels_use_configured_wording():
    assert reason_labels(["market_decline"]) == [OUTCOME_REVIEW_REASONS["market_decline"]]
