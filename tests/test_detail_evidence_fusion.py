from src.detail_evidence_fusion import build_detail_evidence_fusion


def test_detail_description_can_add_hidden_variant_without_becoming_value_evidence():
    out = build_detail_evidence_fusion({
        "titel": "Connor Bedard rookie card",
        "raw_text": "Connor Bedard rookie card",
        "full_description": "Connor Bedard Young Guns High Gloss 07/10 card #451",
    })
    assert out["score"] > 0
    assert any("parallel/variant" in x or "serienämnare" in x or "kortnummer" in x for x in out["discoveries"])
    assert out["safe_for_valuation"] is False


def test_title_and_detail_same_identity_are_corroborated():
    out = build_detail_evidence_fusion({
        "titel": "Connor Bedard Young Guns #451 High Gloss /10",
        "raw_text": "Connor Bedard Young Guns #451 High Gloss /10",
        "full_description": "Connor Bedard Young Guns #451 High Gloss 7/10",
    })
    assert not out["has_conflict"]
    assert "kortnummer" in out["corroborated_fields"] or "parallel/variant" in out["corroborated_fields"]


def test_serial_denominator_conflict_is_explicit():
    out = build_detail_evidence_fusion({
        "titel": "Connor Bedard Young Guns High Gloss 7/10",
        "full_description": "Connor Bedard Young Guns High Gloss 7/25",
    })
    assert out["has_conflict"]
    assert any("serienämnare" in x for x in out["conflicts"])
    assert "Konflikt" in out["status"]


def test_visual_can_corroborate_detail_but_not_create_safe_valuation():
    out = build_detail_evidence_fusion(
        {
            "titel": "Connor Bedard rookie card",
            "full_description": "Connor Bedard Young Guns High Gloss #451 7/10",
        },
        visual_findings={
            "player_name": "Connor Bedard",
            "set_or_product": "Young Guns",
            "card_number": "451",
            "parallel_or_variant": "High Gloss",
            "serial_numerator": 7,
            "serial_denominator": 10,
            "overall_confidence": 0.88,
            "rookie_marker_visible": "yes",
            "autograph_visible": "no",
            "relic_or_patch_visible": "no",
        },
    )
    assert out["visual_included"] is True
    assert not out["has_conflict"]
    assert out["score"] >= 60
    assert out["safe_for_valuation"] is False


def test_visual_conflict_is_not_silently_merged():
    out = build_detail_evidence_fusion(
        {"titel": "Connor Bedard Young Guns #451 /10"},
        visual_findings={
            "player_name": "Connor Bedard",
            "set_or_product": "Young Guns",
            "card_number": "452",
            "serial_denominator": 25,
            "overall_confidence": 0.9,
        },
    )
    assert out["has_conflict"]
    assert len(out["conflicts"]) >= 1

def test_fusion_output_contains_no_monetary_decision_fields():
    out = build_detail_evidence_fusion({
        "titel": "Connor Bedard Young Guns High Gloss #451 /10",
        "full_description": "Connor Bedard Young Guns High Gloss #451 /10",
    })
    forbidden = {"market_value", "value", "profit", "roi", "max_bid", "buy_decision", "expected_resale"}
    assert forbidden.isdisjoint(out.keys())
