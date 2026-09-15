from src.visual_purchase_safety import assess_visual_purchase_safety
from src.visual_detective import response_schema


def _finding(**updates):
    row = {
        "overall_confidence": 0.85, "identity_confidence": 0.85,
        "photo_quality": "good", "front_visible": "yes", "back_visible": "yes",
        "back_text_readable": "yes", "autograph_visible": "no", "autograph_type": "none",
        "grading_company": None, "slab_cert_number": None, "possible_tampering": "no",
        "needs_closeup": False,
    }
    row.update(updates)
    return row


def test_clear_front_and_back_can_continue_to_purchase_review():
    out = assess_visual_purchase_safety(_finding())
    assert out["safe_for_purchase_review"] is True


def test_printed_signature_blocks_purchase_review():
    out = assess_visual_purchase_safety(_finding(autograph_visible="yes", autograph_type="printed_or_facsimile"))
    assert out["safe_for_purchase_review"] is False
    assert any("autograf" in x for x in out["blockers"])


def test_visual_conflict_and_tampering_are_hard_stops():
    out = assess_visual_purchase_safety(_finding(possible_tampering="yes"), {"conflicts": ["kortnummer skiljer sig"]})
    assert out["safe_for_purchase_review"] is False
    assert len(out["blockers"]) >= 2


def test_schema_requires_per_image_evidence_and_slab_fields():
    required = set(response_schema()["required"])
    assert {"per_image_observations", "slab_cert_number", "possible_tampering"} <= required
