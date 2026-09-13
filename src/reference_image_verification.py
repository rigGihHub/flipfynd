"""Reference-trait verification for visual oddity candidates.

A curated registry hit becomes a concrete A/B/C checklist. The result is only a
research aid: it never creates exact identity, SOLD evidence, valuation or BUY.
"""
from __future__ import annotations
import re
from src.oddity_registry import match_curated_cards


def _norm(v: object) -> str:
    return re.sub(r"[^a-z0-9åäö]+", " ", str(v or "").casefold()).strip()


def _blob(findings: dict) -> str:
    values = []
    for key in ("visual_clues", "oddity_observations", "condition_clues", "uncertainties"):
        values.extend(str(x) for x in (findings.get(key) or []))
    for key in ("player_name", "set_or_product", "season_or_year", "card_number", "parallel_or_variant"):
        if findings.get(key):
            values.append(str(findings.get(key)))
    return _norm(" ".join(values))


def _evidence_for_category(category: str, findings: dict, text: str) -> tuple[bool, str]:
    checks = {
        "MISSING_PRINT": (findings.get("possible_missing_print") == "yes" or any(t in text for t in ("saknas", "missing", "no name", "nnof", "namnfält", "folie saknas")), "saknad tryck/text/folie syns"),
        "IMAGE_VARIATION": (findings.get("possible_image_orientation_issue") == "yes" or any(t in text for t in ("spegel", "mirror", "reverse", "fel foto", "wrong photo")), "foto/orientering avviker"),
        "CENSORSHIP": (findings.get("possible_censorship_or_edit") == "yes" or any(t in text for t in ("censur", "marlboro", "blackout", "scribble", "retusch")), "censur/ändring syns"),
        "BACKGROUND_STORY": (findings.get("possible_background_story") == "yes" or any(t in text for t in ("bakgrund", "background", "person", "cameo", "courtside")), "relevant bakgrundsdetalj syns"),
        "PROMO_TEST": (findings.get("possible_factory_or_promo_marker") == "yes" or any(t in text for t in ("promo", "sample", "prototype", "test", "factory")), "promo/test/factory-markering syns"),
    }
    return checks.get(category, (False, "ingen kategorispecifik visuell signal"))


def verify_against_reference_traits(findings: dict | None, *, title: str = "", sport: str = "") -> dict:
    findings = findings or {}
    features = {
        "set_name": findings.get("set_or_product"),
        "season": findings.get("season_or_year"),
        "card_number": findings.get("card_number"),
        "parallel": findings.get("parallel_or_variant"),
        "player_name": findings.get("player_name"),
    }
    matches = match_curated_cards(title=title, sport=sport, player_name=findings.get("player_name") or "", features=features)
    if not matches:
        return {"status": "Ingen dokumenterad referensvariant matchad", "matches": [], "best_score": 0.0, "research_only": True, "can_create_market_value": False, "can_create_buy_decision": False}

    text = _blob(findings)
    quality = str(findings.get("photo_quality") or "unknown").lower()
    front = str(findings.get("front_visible") or "unknown").lower()
    back = str(findings.get("back_visible") or "unknown").lower()
    out = []
    for row in matches:
        visual_ok, visual_reason = _evidence_for_category(row.get("category", ""), findings, text)
        identity_conf = float(findings.get("identity_confidence") or 0)
        oddity_conf = float(findings.get("oddity_confidence") or 0)
        score = 20.0 + (30.0 if visual_ok else 0.0)
        score += min(20.0, identity_conf * 20.0)
        score += min(20.0, oddity_conf * 20.0)
        score += 10.0 if quality in {"good", "excellent"} and front == "yes" else 0.0
        contradictory = bool(findings.get("ordinary_damage_only"))
        if contradictory:
            score = min(score, 35.0)
        score = round(min(100.0, score), 1)

        if contradictory:
            status = "Avvikelsen ser mer ut som skick/produktionsfel"
        elif not visual_ok:
            status = "Identiteten matchar registret men kännetecknet är inte visuellt bekräftat"
        elif score >= 80:
            status = "Stark referensmatch – manuell A/B-kontroll återstår"
        elif score >= 60:
            status = "Möjlig referensmatch – bättre foto eller fler kännetecken behövs"
        else:
            status = "Svag referensmatch"

        checklist = []
        for i, trait in enumerate(row.get("reference_traits") or (), start=1):
            checklist.append({"label": chr(64+i), "expected": trait, "observed": visual_ok if i == 1 else None})
        for trait in row.get("normal_traits") or ():
            checklist.append({"label": "NORMAL", "expected": trait, "observed": None})

        next_steps = [
            "jämför annonsbilden sida vid sida med en dokumenterad referensbild",
            "bekräfta minst två variant-specifika visuella kännetecken när sådana finns",
            "uteslut glare, skada, fotoartefakt och slumpmässigt tryckfel",
        ]
        if quality not in {"good", "excellent"} or front != "yes":
            next_steps.insert(0, "hämta skarpare frontbild innan variantbedömning")
        if back != "yes":
            next_steps.append("hämta baksida om checklist-/copyrightdetaljer behövs")
        next_steps.append("verifiera därefter exact SOLD för exakt samma variant")

        out.append({
            "key": row.get("key"), "title": row.get("title"), "category": row.get("category"),
            "score": score, "status": status, "visual_signal": visual_ok,
            "visual_reason": visual_reason, "checklist": checklist,
            "normal_version_notes": list(row.get("normal_traits") or ()),
            "next_steps": next_steps,
            "reference_image_available": False,
            "reference_image_note": "Registret innehåller kännetecken men ingen inbäddad upphovsrättsskyddad referensbild. Använd auktoritativ checklist-/referenskälla vid slutverifiering.",
        })
    out.sort(key=lambda x: x["score"], reverse=True)
    best = out[0]
    return {
        "status": best["status"], "best_score": best["score"], "matches": out,
        "research_only": True, "can_create_identity": False, "can_create_sold_comp": False,
        "can_create_market_value": False, "can_create_buy_decision": False,
        "note": "Referensmatch betyder visuell förenlighet, inte verifierad variant eller värdepremie.",
    }
