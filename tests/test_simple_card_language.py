from src.simple_card_language import sold_evidence_text, identity_text, sellability_text, compact_evidence_summary


def test_sold_evidence_is_factual_not_scored():
    assert sold_evidence_text(0) == "Saknar verifierade försäljningar"
    assert sold_evidence_text(1) == "1 verifierad försäljning"
    assert sold_evidence_text(4) == "4 verifierade försäljningar"


def test_identity_status_is_translated_without_upgrading_it():
    assert "tydligt identifierat" in identity_text("VERIFIERAD")
    assert "behöver identifieras säkrare" in identity_text("GRANSKA")
    assert "för osäker" in identity_text("LÅST")


def test_sellability_uses_existing_label_or_score_only():
    assert sellability_text("Mycket lättsålt") == "Lätt att sälja"
    assert sellability_text("Trögsålt") == "Svårare att sälja"
    assert sellability_text(None, None) == "Säljbarhet ej verifierad"


def test_compact_summary_does_not_create_decision_fields():
    item={"exact_identity_gate_status":"VERIFIERAD","sold_comparable_count":3,"liquidity_label":"Lättsålt","decision":"BEVAKA"}
    out=compact_evidence_summary(item)
    assert out == ["Kortet är tydligt identifierat", "3 verifierade försäljningar", "Lätt att sälja"]
    assert item["decision"] == "BEVAKA"
