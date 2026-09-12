from src.card_explanation import build_card_explanation


def test_low_numbered_variant_is_compared_with_base_card_without_price_claim():
    out = build_card_explanation({
        "variant_hierarchy_variant_rung": 4,
        "variant_hierarchy_variant_label": "Numrerad /25",
        "sold_comparable_count": 2,
        "exact_identity_status": "EXACT",
    })
    text = " ".join(out["comparison"])
    assert "baskort" in text
    assert "Numrerad /25" in text
    assert "marknadsvärde" not in text.lower()


def test_safe_rookie_program_gets_structural_comparison_to_later_card():
    out = build_card_explanation({
        "rookie_importance_matched": True,
        "rookie_importance_safe_key": True,
        "rookie_importance_key_status": "Starkt lokalt stöd för centralt rookieprogram",
        "variant_hierarchy_rookie_rung": 4,
        "variant_hierarchy_rookie_label": "Rookie Autograph",
    })
    text = " ".join(out["comparison"])
    assert "rookie" in text.lower()
    assert "veterankort" in text.lower()


def test_weak_card_explains_what_evidence_is_missing():
    out = build_card_explanation({"titel": "Star player base card"})
    assert out["strengths"] == []
    assert out["stronger_if"]
    assert any("SOLD" in x or "kortidentitet" in x for x in out["stronger_if"])
