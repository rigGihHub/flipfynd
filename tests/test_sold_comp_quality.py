from src.sold_comp_quality import audit_sold_comp_records, classify_sold_comp, is_verified_sold_comp


def _verified(**extra):
    row = {
        "titel": "Connor McDavid 2023 card",
        "sold_price": 199.0,
        "sold_verification_status": "verified",
        "sale_evidence_type": "explicit_sold_price",
        "source_platform": "Tradera",
    }
    row.update(extra)
    return row


def test_verified_explicit_sale_is_safe():
    result = classify_sold_comp(_verified())
    assert result["safe_for_valuation"] is True
    assert is_verified_sold_comp(_verified()) is True


def test_numeric_sold_price_without_verification_is_blocked():
    result = classify_sold_comp({"titel": "Card", "sold_price": 100.0})
    assert result["safe_for_valuation"] is False
    assert result["reason"] == "missing_verified_status"


def test_sold_word_without_evidence_metadata_is_blocked():
    result = classify_sold_comp({
        "titel": "Card", "sold_price": 100.0,
        "market_state": "sold", "sold_verification_status": "verified",
    })
    assert result["safe_for_valuation"] is False
    assert result["reason"] == "missing_explicit_sale_evidence_metadata"


def test_verified_row_requires_positive_realised_price():
    result = classify_sold_comp(_verified(sold_price=0))
    assert result["safe_for_valuation"] is False
    assert result["reason"] == "missing_positive_realised_price"


def test_audit_separates_safe_and_blocked_rows():
    rows = [_verified(sold_at="2026-09-01", lank="https://example.test/1"), {"sold_price": 88.0}]
    audit = audit_sold_comp_records(rows)
    assert audit["total_count"] == 2
    assert audit["safe_count"] == 1
    assert audit["blocked_count"] == 1
    assert audit["strong_count"] == 1
    assert audit["rejection_reasons"]["missing_verified_status"] == 1
