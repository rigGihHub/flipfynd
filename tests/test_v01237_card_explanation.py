from src.card_explanation import build_card_explanation


def test_explanation_surfaces_existing_card_strengths_without_inventing_value():
    item = {
        "collector_worth_strengths": ["Lågnumrerad parallel med tydlig samlarrelevans"],
        "card_hierarchy_tier_label": "Premium / relevant",
        "card_hierarchy_score": 82,
        "sold_comparable_count": 3,
        "liquidity_label": "God",
        "liquidity_score": 74,
    }
    out = build_card_explanation(item)
    assert "Lågnumrerad" in " ".join(out["strengths"])
    assert any("Verifierade SOLD-jämförelser: 3" == x for x in out["evidence"])
    assert not any("marknadsvärde" in x.lower() for x in out["strengths"])


def test_explanation_is_honest_when_no_verified_strength_exists():
    out = build_card_explanation({"titel": "Wayne Gretzky base card"})
    assert out["strengths"] == []
    assert "ingen verifierad" in out["headline"].lower()
    assert any("räcker inte" in x for x in out["cautions"])


def test_explanation_preserves_rookie_caution():
    out = build_card_explanation({"rookie_claim_support": "CHRONOLOGICALLY_SUSPICIOUS"})
    assert any("kronologiskt tveksamt" in x for x in out["cautions"])
