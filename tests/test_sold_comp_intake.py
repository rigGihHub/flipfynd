from src.sold_comp_import import normalize_sold_comp
from src.sold_comp_intake import review_sold_comp_intake, sold_comp_intake_audit


def sold_row(**extra):
    row = {
        "titel": "Connor Bedard Upper Deck Young Guns #451",
        "sold_price": 1200,
        "sold_verification_status": "verified",
        "sale_evidence_type": "explicit_sold_price",
        "source_platform": "test",
    }
    row.update(extra)
    return row


def test_verified_sale_without_identity_is_sale_only():
    result = review_sold_comp_intake(sold_row())
    assert result["sale_verified"] is True
    assert result["exact_identity_ready"] is False
    assert result["status"] == "SALE_ONLY"


def test_complete_identity_without_confirmation_needs_review():
    result = review_sold_comp_intake(sold_row(
        player_name="Connor Bedard", set_name="Upper Deck", season="2023-24", card_number="451"
    ))
    assert result["status"] == "IDENTITY_REVIEW"
    assert result["exact_identity_ready"] is False


def test_confirmed_structured_identity_is_exact_ready():
    result = review_sold_comp_intake(sold_row(
        player_name="Connor Bedard", set_name="Upper Deck", season="2023-24", card_number="451",
        identity_verified=True, identity_evidence_source="checklist + listing images",
    ))
    assert result["status"] == "EXACT_READY"
    assert result["valuation_ready"] is True


def test_conflict_blocks_exact_ready():
    result = review_sold_comp_intake(sold_row(
        player_name="Connor Bedard", set_name="Upper Deck", season="2023-24", card_number="451",
        identity_verified=True, identity_conflicts=["kortnummer 451 vs 452"],
    ))
    assert result["exact_identity_ready"] is False


def test_special_variant_requires_structured_variant_name():
    result = review_sold_comp_intake(sold_row(
        player_name="Connor Bedard", set_name="Upper Deck", season="2023-24", card_number="451",
        identity_verified=True, is_parallel=True,
    ))
    assert result["exact_identity_ready"] is False
    assert any("parallel" in b for b in result["blockers"])


def test_normalize_preserves_explicit_identity_metadata():
    record = normalize_sold_comp({
        "title": "Connor Bedard #451", "sold_price": 1000, "currency": "SEK",
        "player_name": "Connor Bedard", "set_name": "Upper Deck", "season": "2023-24",
        "card_number": "451", "identity_verified": True,
        "identity_evidence_source": "manual checklist review",
    })
    assert record["player_name"] == "Connor Bedard"
    assert record["card_number"] == "451"
    assert record["identity_verified"] is True


def test_audit_keeps_sale_and_identity_counts_separate():
    audit = sold_comp_intake_audit([
        sold_row(),
        sold_row(player_name="A", set_name="B", season="2024", card_number="1", identity_verified=True),
        {"titel": "active listing", "sold_price": 20},
    ])
    assert audit["sale_only_count"] == 1
    assert audit["exact_ready_count"] == 1
    assert audit["rejected_count"] == 1
