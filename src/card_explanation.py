"""Evidence-aware explanation of why a listing's card is (or is not) interesting.

This module deliberately reuses signals that already exist in FlipFynd. It does
not invent card facts, market values, rookie status or rarity.
"""
from __future__ import annotations


def _unique(values):
    out = []
    seen = set()
    for value in values:
        text = str(value).strip() if value not in (None, "") else ""
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _comparison_context(item: dict) -> list[str]:
    """Explain where this exact version sits relative to more ordinary cards.

    Wording is intentionally structural. We only compare against generic card
    classes when the existing hierarchy engines support that distinction.
    """
    comparisons: list[str] = []

    variant_rung = item.get("variant_hierarchy_variant_rung")
    variant_label = item.get("variant_hierarchy_variant_label")
    rookie_rung = item.get("variant_hierarchy_rookie_rung")
    rookie_label = item.get("variant_hierarchy_rookie_label")

    if isinstance(variant_rung, (int, float)):
        if variant_rung >= 5:
            comparisons.append(
                f"Det här är strukturellt långt över ett vanligt baskort: {variant_label or 'mycket knapp/premium variant'}."
            )
        elif variant_rung >= 3:
            comparisons.append(
                f"Det här är en tydligare samlarvariant än ett vanligt baskort: {variant_label or 'numrerad/premium variant'}."
            )
        elif variant_rung == 2:
            comparisons.append(
                f"Det här verkar vara en parallel snarare än standardversionen: {variant_label or 'parallel'}."
            )
        elif variant_rung <= 0:
            comparisons.append(
                "FlipFynd har inte verifierat någon variantnivå som placerar kortet över ett vanligt baskort."
            )

    if isinstance(rookie_rung, (int, float)) and rookie_rung > 0:
        if rookie_rung >= 4:
            comparisons.append(
                f"Rookie-strukturen är starkare än ett generiskt RC/baskort: {rookie_label or 'premium rookievariant'}."
            )
        elif rookie_rung >= 2:
            comparisons.append(
                f"Kortet är kopplat till en dokumenterad rookiehierarki ({rookie_label or 'rookieprogram'}), men exakt betydelse måste fortfarande verifieras."
            )

    key_status = item.get("rookie_importance_key_status")
    if item.get("rookie_importance_matched") and key_status:
        if item.get("rookie_importance_safe_key"):
            comparisons.append(
                "Det finns lokalt stöd för att detta är ett centralt rookieprogram för just spelaren – starkare än ett vanligt senare veterankort."
            )
        else:
            comparisons.append(
                f"Rookieprogrammet är intressant, men FlipFynd bedömer fortfarande: {key_status}."
            )

    role = str(item.get("card_hierarchy_role") or "").casefold()
    role_label = item.get("card_hierarchy_role_label")
    if role in {"base", "standard", "base_card"}:
        comparisons.append(
            "Kortets roll ser ut som bas/standard. Spelarens namn kan vara starkt, men just den här versionen får därför inget extra samlarvärde enbart av spelaren."
        )
    elif role_label and not comparisons:
        comparisons.append(f"Kortets dokumenterade roll i hobbyhierarkin är: {role_label}.")

    return _unique(comparisons)[:5]


def _what_would_make_it_stronger(item: dict) -> list[str]:
    next_steps: list[str] = []

    if not item.get("rookie_importance_safe_key") and item.get("rookie_importance_matched"):
        next_steps.append("Verifierad checklist/programkälla som visar exakt rookieprogram och variant.")

    sold_count = item.get("sold_comparable_count")
    if sold_count is None:
        sold_count = item.get("sold_comps")
    if not isinstance(sold_count, (int, float)) or sold_count < 3:
        next_steps.append("Fler exact SOLD-jämförelser med samma kort, variant och numrering.")

    identity_status = str(item.get("exact_identity_status") or "").casefold()
    if not identity_status or not any(token in identity_status for token in ("exact", "säker", "verified", "verifier")):
        next_steps.append("Säkrare exakt kortidentitet: set/program, år, kortnummer och variant.")

    if not isinstance(item.get("variant_hierarchy_variant_rung"), (int, float)):
        next_steps.append("Verifierad variant-/raritetsinformation som skiljer kortet från standardversionen.")

    return _unique(next_steps)[:4]



def build_card_identity_summary(item: dict) -> dict:
    """Return a compact, evidence-aware identity card for the listing.

    The summary prefers fields from Exact Identity Gate because those are the
    fields FlipFynd has already normalized for exact-comp decisions. Missing
    facts stay explicitly unknown instead of being inferred from the title.
    """
    item = item or {}
    fields = item.get("exact_identity_gate_identity_fields") or {}
    if not isinstance(fields, dict):
        fields = {}

    def pick(name, *fallbacks):
        value = fields.get(name)
        if value not in (None, ""):
            return value
        for key in fallbacks:
            value = item.get(key)
            if value not in (None, ""):
                return value
        return None

    rows = []
    missing = []

    def add(label, value, missing_label=None):
        if value in (None, ""):
            rows.append({"label": label, "value": "Ej säkert identifierat", "known": False})
            if missing_label:
                missing.append(missing_label)
        else:
            rows.append({"label": label, "value": str(value), "known": True})

    add("Spelare", pick("player_name", "player_name"), "spelare")
    add("Set / program", pick("set_name", "set_name"), "set/program")
    add("Säsong / år", pick("season", "rookie_window_card_year"), "säsong/år")

    card_number = pick("card_number", "card_number")
    if card_number not in (None, ""):
        card_number = str(card_number)
        if not card_number.startswith("#"):
            card_number = "#" + card_number
    add("Kortnummer", card_number, "kortnummer")

    variant = pick("parallel", "parallel") or item.get("variant_hierarchy_variant_label")
    add("Variant / parallel", variant)

    serial = pick("serial_denominator", "serial_number")
    serial_display = None
    if serial not in (None, ""):
        serial_text = str(serial).strip().lstrip("/")
        serial_display = f"Numrerad till /{serial_text}"
    add("Numrering", serial_display)

    rookie_signal = fields.get("is_rookie")
    if item.get("official_rookie_year_verified") and item.get("official_rookie_year"):
        rookie_value = f"Verifierat rookieår: {item.get('official_rookie_year')}"
    elif rookie_signal:
        rookie_value = "Rookie/RC-signal finns – officiellt rookieår ej verifierat"
    elif item.get("rookie_claim_support") == "CHRONOLOGICALLY_SUSPICIOUS":
        rookie_value = "Rookie/RC-anspråk är kronologiskt tveksamt"
    else:
        rookie_value = "Ingen verifierad rookie-status"
    rows.append({"label": "Rookie / RC", "value": rookie_value, "known": bool(item.get("official_rookie_year_verified"))})

    traits = []
    if fields.get("is_auto"):
        traits.append("Autograf")
    if fields.get("is_patch"):
        traits.append("Patch / memorabilia")
    grading_company = pick("grading_company", "grading_company")
    grade = pick("grade", "grade")
    if grading_company or grade:
        grading = " ".join(str(x) for x in (grading_company, grade) if x not in (None, ""))
        traits.append(f"Graderad: {grading}")
    rows.append({"label": "Specialegenskaper", "value": ", ".join(traits) if traits else "Inga verifierade specialegenskaper", "known": bool(traits)})

    gate_status = item.get("exact_identity_gate_status") or "LÅST"
    gate_label = item.get("exact_identity_gate_label") or "Exakt identitet inte verifierad"
    gate_score = item.get("exact_identity_gate_score")
    status_text = gate_label
    if isinstance(gate_score, (int, float)):
        status_text += f" · {float(gate_score):.0f}/100"

    # Prefer the gate's own missing-field list where available.
    gate_missing = item.get("exact_identity_gate_blockers") or []
    return {
        "rows": rows,
        "status": str(gate_status),
        "status_text": status_text,
        "missing": _unique(missing),
        "blockers": _unique(gate_missing)[:4],
        "supports_exact_comp_search": bool(item.get("exact_identity_gate_supports_exact_comp_search")),
    }

def _rarity_context(item: dict) -> list[str]:
    rows = item.get("rarity_evidence_entries") or []
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows[:3]:
        if not isinstance(row, dict):
            continue
        label = row.get("label")
        status = row.get("status")
        if label and status:
            hierarchy = row.get("collectible_hierarchy_label")
            suffix = f" · {hierarchy}" if hierarchy else ""
            out.append(f"{label}: {status}{suffix}.")
    if item.get("rarity_evidence_unsupported_count"):
        out.append("Minst ett SSP/case-hit-påstående saknar källstöd och ska behandlas som osäkert.")
    return _unique(out)[:4]


def build_card_explanation(item: dict) -> dict:
    item = item or {}
    strengths = []
    cautions = []
    evidence = []

    # Best available card/hobby knowledge first.
    strengths.extend(item.get("collector_worth_strengths") or [])
    strengths.extend(item.get("collector_worth_value_basis") or [])
    strengths.extend(item.get("card_hierarchy_reasons") or [])
    strengths.extend(item.get("player_card_hierarchy_reasons") or [])
    strengths.extend(item.get("rookie_window_reasons") or [])
    strengths.extend(item.get("rookie_importance_reasons") or [])

    hierarchy_label = item.get("card_hierarchy_tier_label")
    hierarchy_role = item.get("card_hierarchy_role_label")
    hierarchy_score = item.get("card_hierarchy_score")
    if hierarchy_label:
        suffix = f" ({float(hierarchy_score):.0f}/100)" if isinstance(hierarchy_score, (int, float)) else ""
        role = f" · {hierarchy_role}" if hierarchy_role else ""
        evidence.append(f"Hobbyhierarki: {hierarchy_label}{role}{suffix}")

    player_card_label = item.get("player_card_hierarchy_label")
    player_card_score = item.get("player_card_hierarchy_score")
    if player_card_label:
        suffix = f" ({float(player_card_score):.0f}/100)" if isinstance(player_card_score, (int, float)) else ""
        evidence.append(f"Spelare × kort: {player_card_label}{suffix}")

    archetype = item.get("player_archetype_label")
    if archetype:
        evidence.append(f"Spelarprofil: {archetype}")

    if item.get("career_context_verified") and item.get("career_status_label"):
        era = f" · {item.get('career_era_label')}" if item.get("career_era_label") else ""
        evidence.append(f"Verifierad karriärkontext: {item.get('career_status_label')}{era}")

    variant_label = item.get("variant_hierarchy_variant_label")
    rookie_label = item.get("variant_hierarchy_rookie_label")
    if variant_label:
        evidence.append(f"Variantnivå: {variant_label}")
    if rookie_label and str(rookie_label).casefold() != "ingen dokumenterad rookiehierarki":
        evidence.append(f"Rookiehierarki: {rookie_label}")

    # Discovery/market-edge signals are interesting, but never proof of value.
    if item.get("is_information_edge_candidate"):
        strengths.extend(item.get("information_edge_reasons") or [])
    if item.get("is_market_edge_candidate"):
        strengths.extend(item.get("market_edge_reasons") or [])
    if item.get("is_hidden_find_candidate"):
        strengths.extend(item.get("hidden_find_reasons") or [])
    if item.get("misclassified_card_candidate"):
        strengths.extend(item.get("misclassified_card_reasons") or [])
    if item.get("mispriced_rookie_candidate"):
        strengths.extend(item.get("mispriced_rookie_reasons") or [])

    # Evidence that supports actual valuation/decision quality.
    sold_count = item.get("sold_comparable_count")
    if sold_count is None:
        sold_count = item.get("sold_comps")
    if isinstance(sold_count, (int, float)):
        evidence.append(f"Verifierade SOLD-jämförelser: {int(sold_count)}")

    identity_status = item.get("exact_identity_status")
    if identity_status:
        evidence.append(f"Identitet: {identity_status}")

    liquidity_label = item.get("liquidity_label")
    liquidity_score = item.get("liquidity_score")
    if liquidity_label:
        suffix = f" ({float(liquidity_score):.0f}/100)" if isinstance(liquidity_score, (int, float)) else ""
        evidence.append(f"Säljbarhet: {liquidity_label}{suffix}")

    # Important caveats from the same intelligence stack.
    cautions.extend(item.get("collector_worth_cautions") or [])
    cautions.extend(item.get("collector_worth_hobby_traps") or [])
    cautions.extend(item.get("card_hierarchy_hobby_traps") or [])
    cautions.extend(item.get("player_card_hierarchy_cautions") or [])
    cautions.extend(item.get("player_card_hierarchy_hobby_traps") or [])
    cautions.extend(item.get("rookie_window_cautions") or [])
    cautions.extend(item.get("rookie_importance_cautions") or [])
    if item.get("rookie_claim_support") == "CHRONOLOGICALLY_SUSPICIOUS":
        cautions.append("Rookie/RC-anspråket ser kronologiskt tveksamt ut och måste verifieras mot checklist/program.")
    if item.get("primary_blocker"):
        cautions.append(item.get("primary_blocker"))

    strengths = _unique(strengths)[:6]
    cautions = _unique(cautions)[:5]
    evidence = _unique(evidence)[:7]
    comparison = _comparison_context(item)
    stronger_if = _what_would_make_it_stronger(item)

    if strengths:
        headline = "Det här är det FlipFynd faktiskt ser som intressant med just den här versionen."
    else:
        headline = "FlipFynd ser ännu ingen verifierad egenskap som gör just den här versionen särskilt stark."
        cautions = _unique([
            "Känt spelarnamn, ord som 'rookie' eller ett premiumset räcker inte i sig som bevis på samlarvärde.",
            *cautions,
        ])[:5]

    return {
        "headline": headline,
        "strengths": strengths,
        "comparison": comparison,
        "evidence": evidence,
        "cautions": cautions,
        "stronger_if": stronger_if,
        "rarity_context": _rarity_context(item),
    }
