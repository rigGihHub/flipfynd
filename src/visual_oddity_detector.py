"""Research-only visual oddity detector.

Turns cautious visual observations into an oddity research plan. It never creates
price, exact SOLD, exact identity or BUY signals. Ordinary damage/printing flaws
are explicitly separated from documented collectible variants.
"""
from __future__ import annotations

from src.oddity_registry import ODDITY_TAXONOMY, match_curated_cards


def _truthy(v):
    return str(v or "").strip().lower() == "yes"


def build_visual_oddity_signal(findings: dict | None, *, title: str = "", sport: str = "") -> dict:
    findings = findings or {}
    categories = []
    reasons = []
    verify = []

    mapping = [
        ("possible_missing_print", "MISSING_PRINT", "Bilden kan visa saknad text, namn, färg eller folie."),
        ("possible_image_orientation_issue", "IMAGE_VARIATION", "Bilden kan avvika i foto/orientering, t.ex. reverse negative eller fel foto."),
        ("possible_censorship_or_edit", "CENSORSHIP", "Bilden kan visa en censurerad/ändrad bild- eller reklamvariant."),
        ("possible_background_story", "BACKGROUND_STORY", "Bilden innehåller en möjlig ovanlig bakgrundsdetalj eller cameo."),
        ("possible_factory_or_promo_marker", "PROMO_TEST", "Bilden kan visa promo/sample/test/factory-only-markering."),
    ]
    for field, category, reason in mapping:
        if _truthy(findings.get(field)):
            categories.append(category)
            reasons.append(reason)

    observations = [str(x).strip() for x in (findings.get("oddity_observations") or []) if str(x).strip()]
    reasons.extend(observations[:6])

    features = {
        "set_name": findings.get("set_or_product"),
        "season": findings.get("season_or_year"),
        "card_number": findings.get("card_number"),
        "parallel": findings.get("parallel_or_variant"),
        "player_name": findings.get("player_name"),
    }
    known = match_curated_cards(
        title=title,
        sport=sport,
        player_name=findings.get("player_name") or "",
        features=features,
    )
    if known:
        categories.extend([x.get("category") for x in known if x.get("category")])
        reasons.append("Visuell identitet är förenlig med ett kort i FlipFynds kuraterade oddity-register.")
        verify.extend([x.get("research") for x in known if x.get("research")])

    ordinary_damage_only = bool(findings.get("ordinary_damage_only"))
    conf = findings.get("oddity_confidence")
    try:
        conf = float(conf) if conf is not None else 0.0
    except (TypeError, ValueError):
        conf = 0.0

    categories = list(dict.fromkeys(c for c in categories if c))
    if categories:
        verify.extend([
            "jämför mot dokumenterad referensbild för exakt variant",
            "kontrollera att avvikelsen inte bara är skada, glare, scan/fotoartefakt eller slumpmässigt tryckfel",
            "verifiera checklist-/variantreferens innan premie antas",
            "jämför först därefter exact SOLD-comps för samma variant",
        ])

    collectible_candidate = bool(categories) and not ordinary_damage_only
    if ordinary_damage_only and categories:
        status = "Visuell avvikelse – ser mer ut som skick/produktionsfel än dokumenterad samlarvariant"
    elif known:
        status = "Känd oddity-kandidat – verifiera visuella kännetecken"
    elif collectible_candidate and conf >= 0.65:
        status = "Möjlig visuell oddity – riktad variantresearch rekommenderas"
    elif collectible_candidate:
        status = "Svag visuell oddity-signal – kräver bättre foto/referens"
    else:
        status = "Ingen tydlig visuell oddity"

    return {
        "candidate": collectible_candidate,
        "status": status,
        "confidence": round(conf * 100, 1),
        "categories": categories,
        "category_labels": [ODDITY_TAXONOMY.get(c, c) for c in categories],
        "reasons": list(dict.fromkeys(reasons))[:10],
        "verify_first": list(dict.fromkeys(x for x in verify if x))[:10],
        "known_registry_matches": [x.get("title") for x in known if x.get("title")],
        "ordinary_damage_only": ordinary_damage_only,
        "research_only": True,
        "can_create_identity": False,
        "can_create_sold_comp": False,
        "can_create_market_value": False,
        "can_create_buy_decision": False,
        "note": "Visuella avvikelser är hypoteser. Ingen premie räknas förrän exakt variant och marknadsdata är verifierade.",
    }
