from src.exact_identity_gate import build_exact_identity_gate


def base():
    return {
        "player_name": "Connor Bedard",
        "player_match_confidence": "high",
        "set_name": "Young Guns",
        "season": "2023-24",
        "card_number": "451",
        "card_identity_confidence_score": 94,
        "identity_evidence_sources": {
            "player_name": ["title", "listing_text"],
            "set_name": ["title", "listing_text"],
            "card_number": ["listing_text"],
        },
        "detail_evidence_fusion_source_count": 2,
    }


def test_strong_multisource_identity_unlocks_both_levels():
    gate = build_exact_identity_gate(base())
    assert gate["status"] == "VERIFIERAD"
    assert gate["supports_exact_comp_search"] is True
    assert gate["supports_dynamic_max_bid"] is True
    assert gate["safe_for_valuation"] is False


def test_single_source_can_search_but_cannot_support_dynamic_bid():
    d = base()
    d["identity_evidence_sources"] = {"player_name": ["title"], "set_name": ["title"], "card_number": ["title"]}
    d["detail_evidence_fusion_source_count"] = 1
    gate = build_exact_identity_gate(d)
    assert gate["supports_exact_comp_search"] is True
    assert gate["supports_dynamic_max_bid"] is False


def test_missing_card_number_locks_exact_identity():
    d = base(); d["card_number"] = None
    gate = build_exact_identity_gate(d)
    assert gate["supports_exact_comp_search"] is False
    assert "kortnummer" in gate["missing_fields"]


def test_identity_conflict_blocks_even_high_score():
    d = base(); d["identity_conflicts"] = ["parallel: titel=High Gloss / annonsinfo=Exclusives"]
    gate = build_exact_identity_gate(d)
    assert gate["supports_exact_comp_search"] is False
    assert gate["supports_dynamic_max_bid"] is False


def test_lot_never_unlocks_exact_identity():
    d = base(); d["is_lot"] = True
    gate = build_exact_identity_gate(d)
    assert gate["status"] == "LÅST"
    assert gate["supports_exact_comp_search"] is False


def test_parallel_is_added_to_exact_comp_requirements():
    d = base(); d["parallel"] = "High Gloss"; d["serial_number"] = 10
    gate = build_exact_identity_gate(d)
    text = " ".join(gate["exact_comp_requirements"])
    assert "High Gloss" in text
    assert "10" in text
