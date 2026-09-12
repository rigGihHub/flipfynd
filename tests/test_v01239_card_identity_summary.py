from src.card_explanation import build_card_identity_summary


def _values(out):
    return {row["label"]: row["value"] for row in out["rows"]}


def test_identity_summary_prefers_exact_gate_fields_and_formats_card_number():
    out = build_card_identity_summary({
        "exact_identity_gate_identity_fields": {
            "player_name": "Connor Bedard",
            "set_name": "Upper Deck Young Guns",
            "season": "2023-24",
            "card_number": "451",
            "parallel": "Outburst",
            "serial_denominator": 25,
            "is_rookie": True,
            "is_auto": False,
            "is_patch": False,
        },
        "exact_identity_gate_status": "SÖKBAR",
        "exact_identity_gate_label": "Exakt identitet – comp-sökning tillåten, maxbud låst",
        "exact_identity_gate_score": 84,
        "exact_identity_gate_supports_exact_comp_search": True,
    })
    values = _values(out)
    assert values["Spelare"] == "Connor Bedard"
    assert values["Kortnummer"] == "#451"
    assert values["Variant / parallel"] == "Outburst"
    assert values["Numrering"] == "Numrerad till /25"
    assert "officiellt rookieår ej verifierat" in values["Rookie / RC"]
    assert out["supports_exact_comp_search"] is True


def test_identity_summary_keeps_unknown_identity_explicitly_unknown():
    out = build_card_identity_summary({"player_name": "Wayne Gretzky"})
    values = _values(out)
    assert values["Spelare"] == "Wayne Gretzky"
    assert values["Set / program"] == "Ej säkert identifierat"
    assert values["Kortnummer"] == "Ej säkert identifierat"
    assert "set/program" in out["missing"]
    assert "kortnummer" in out["missing"]
    assert out["supports_exact_comp_search"] is False


def test_identity_summary_does_not_convert_rookie_signal_into_official_rookie_year():
    out = build_card_identity_summary({
        "exact_identity_gate_identity_fields": {"is_rookie": True},
        "official_rookie_year_verified": False,
        "official_rookie_year": None,
    })
    values = _values(out)
    assert "officiellt rookieår ej verifierat" in values["Rookie / RC"]
    assert "Verifierat rookieår" not in values["Rookie / RC"]
