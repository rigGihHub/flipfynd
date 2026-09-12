"""Optional image-level card detective for FlipFynd.

The detector is deliberately isolated from valuation. It can create *visual
hypotheses* from listing images, but it never changes estimated value, profit,
ROI, max bid or buy decision. Findings must be verified against title/raw text,
checklists and market comps before they may be treated as facts.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

SYSTEM_PROMPT = """
Du är FlipFynds försiktiga bildgranskare för samlarkort (hockey och fotboll).
Du ska granska ALLA bifogade annonsbilder tillsammans och försöka avgöra vad
som faktiskt går att läsa eller se på kortets fram- och baksida.

Arbeta som en erfaren samlarkortsgranskare:
1. Leta efter spelarnamn, lag/klubb, set-/produktlogotyp, säsong/år och kortnummer.
2. Leta efter tryckt serialisering (t.ex. 12/25), RC/rookie-logga, parallel-/variantnamn,
   autograph-/stickerindikator, patch/relic-fönster och graderingsetikett.
3. Använd baksidan för checklist-/kortnummer, copyright-/årtal och setidentifiering när den syns.
4. Skilj ett faktiskt synligt namn/nummer/logotyp från en slutsats baserad på designen.
5. Bedöm även om fotona är tillräckliga för identifikation: fram/baksida, skärpa,
   blänk, beskärning och om ett närfoto behövs.
6. För skick: rapportera bara synliga observationer (t.ex. tydligt hörnslitage,
   kantvitning, kraftig off-centering, repa eller crease). Sätt aldrig en PSA/BGS-liknande grade.

Absoluta regler:
- Gissa aldrig kortnummer, serienummer, parallel, rookie-status, autograf, patch/relic,
  set, år, spelare eller lag.
- Om detaljen inte går att läsa tydligt: använd null/unknown och låg confidence.
- En tryckt/faksimil-signatur får inte kallas äkta autograf.
- Ett glansigt/färgat kort får inte automatiskt kallas en specifik parallel.
- Designlikhet får beskrivas som ledtråd, aldrig som verifierad identitet.
- Svara inte med pris, marknadsvärde, ROI, vinst, maxbud eller köprekommendation.
- Annonstexten är endast kontext och får inte användas som bevis för vad bilden visar.
- Svara endast med JSON enligt schemat.
""".strip()


def response_schema() -> dict[str, Any]:
    nullable_string = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    nullable_int = {"anyOf": [{"type": "integer"}, {"type": "null"}]}
    nullable_number = {"anyOf": [{"type": "number", "minimum": 0, "maximum": 1}, {"type": "null"}]}
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "player_name": nullable_string,
            "team_or_club": nullable_string,
            "set_or_product": nullable_string,
            "season_or_year": nullable_string,
            "card_number": nullable_string,
            "serial_numerator": nullable_int,
            "serial_denominator": nullable_int,
            "parallel_or_variant": nullable_string,
            "rookie_marker_visible": {"type": "string", "enum": ["yes", "no", "unknown"]},
            "autograph_visible": {"type": "string", "enum": ["yes", "no", "unknown"]},
            "autograph_type": {"type": "string", "enum": ["on_card", "sticker", "printed_or_facsimile", "unclear", "none", "unknown"]},
            "relic_or_patch_visible": {"type": "string", "enum": ["yes", "no", "unknown"]},
            "grading_company": nullable_string,
            "grade": nullable_string,
            "front_visible": {"type": "string", "enum": ["yes", "no", "unknown"]},
            "back_visible": {"type": "string", "enum": ["yes", "no", "unknown"]},
            "back_text_readable": {"type": "string", "enum": ["yes", "no", "unknown"]},
            "foil_or_holo_visible": {"type": "string", "enum": ["yes", "no", "unknown"]},
            "photo_quality": {"type": "string", "enum": ["poor", "fair", "good", "excellent", "unknown"]},
            "identity_confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "variant_confidence": nullable_number,
            "condition_confidence": nullable_number,
            "overall_confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "needs_back_image": {"type": "boolean"},
            "needs_closeup": {"type": "boolean"},
            "recommended_next_photo": nullable_string,
            "condition_clues": {"type": "array", "items": {"type": "string"}},
            "visual_clues": {"type": "array", "items": {"type": "string"}},
            "uncertainties": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "player_name", "team_or_club", "set_or_product", "season_or_year", "card_number",
            "serial_numerator", "serial_denominator", "parallel_or_variant",
            "rookie_marker_visible", "autograph_visible", "autograph_type", "relic_or_patch_visible",
            "grading_company", "grade", "front_visible", "back_visible", "back_text_readable",
            "foil_or_holo_visible", "photo_quality", "identity_confidence", "variant_confidence",
            "condition_confidence", "overall_confidence", "needs_back_image", "needs_closeup",
            "recommended_next_photo", "condition_clues", "visual_clues", "uncertainties",
        ],
    }


def _norm(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def _serial_string(result: dict) -> str | None:
    n = result.get("serial_numerator")
    d = result.get("serial_denominator")
    if isinstance(n, int) and isinstance(d, int) and 0 < n <= d:
        return f"{n}/{d}"
    return None


def visual_identity_completeness(result: dict) -> dict[str, Any]:
    """Summarise how much exact identity the photos actually support."""
    key_fields = {
        "spelare": result.get("player_name"),
        "set/produkt": result.get("set_or_product"),
        "år/säsong": result.get("season_or_year"),
        "kortnummer": result.get("card_number"),
        "parallel/variant": result.get("parallel_or_variant"),
    }
    if _serial_string(result):
        key_fields["serienummer"] = _serial_string(result)

    known = [label for label, value in key_fields.items() if value not in (None, "")]
    missing = [label for label, value in key_fields.items() if value in (None, "")]
    score = int(round(100 * len(known) / max(1, len(key_fields))))

    if result.get("back_visible") == "yes" and result.get("back_text_readable") == "yes":
        score = min(100, score + 8)
    if float(result.get("identity_confidence") or 0) < 0.55:
        score = min(score, 49)

    if score >= 85 and float(result.get("identity_confidence") or 0) >= 0.75:
        status = "Stark visuell identitet"
    elif score >= 60:
        status = "Delvis identifierat"
    else:
        status = "Otillräcklig bildidentitet"

    return {
        "score": score,
        "status": status,
        "known_fields": known,
        "missing_fields": missing,
        "front_visible": result.get("front_visible", "unknown"),
        "back_visible": result.get("back_visible", "unknown"),
        "photo_quality": result.get("photo_quality", "unknown"),
        "needs_back_image": bool(result.get("needs_back_image")),
        "needs_closeup": bool(result.get("needs_closeup")),
        "recommended_next_photo": result.get("recommended_next_photo"),
        "safe_for_valuation": False,
    }


def compare_visual_to_listing(result: dict, title: str = "", raw_text: str = "") -> dict:
    """Compare visual hypotheses with listing text without promoting them to facts."""
    listing_n = _norm(f"{title} {raw_text}")
    discoveries: list[str] = []
    conflicts: list[str] = []

    fields = [
        ("spelare", result.get("player_name")),
        ("lag/klubb", result.get("team_or_club")),
        ("set/produkt", result.get("set_or_product")),
        ("år/säsong", result.get("season_or_year")),
        ("kortnummer", result.get("card_number")),
        ("parallel/variant", result.get("parallel_or_variant")),
        ("grading", " ".join(x for x in [str(result.get("grading_company") or ""), str(result.get("grade") or "")] if x).strip()),
    ]
    serial = _serial_string(result)
    if serial:
        fields.append(("serienummer", serial))

    for label, value in fields:
        if not value:
            continue
        value_n = _norm(value)
        if value_n and value_n not in listing_n:
            discoveries.append(f"Bilden antyder {label}: {value}, men detta saknas i annonstexten")

    yes_terms = [
        ("rookie/RC-markering", result.get("rookie_marker_visible") == "yes", ("rookie", " rc ", "young guns", "rated rookie")),
        ("autograf", result.get("autograph_visible") == "yes", ("auto", "autograf", "autograph", "signerad")),
        ("patch/relic", result.get("relic_or_patch_visible") == "yes", ("patch", "relic", "jersey", "memorabilia")),
    ]
    padded = f" {listing_n} "
    for label, is_yes, terms in yes_terms:
        if is_yes and not any(term in padded for term in terms):
            discoveries.append(f"Bilden antyder {label}, men annonstexten nämner inte det")

    if serial:
        visual_den = str(result.get("serial_denominator"))
        listing_dens = {m.group(1) for m in re.finditer(r"/(\d{1,4})(?!\d)", listing_n)}
        if listing_dens and visual_den not in listing_dens:
            conflicts.append(f"Bildhypotesen anger /{visual_den}, medan annonstexten anger /{'/'.join(sorted(listing_dens))}")

    card_no = _norm(result.get("card_number"))
    if card_no:
        listing_card_nums = {m.group(1).lower() for m in re.finditer(r"(?:card\s*#?|no\.?|nr\.?|#)\s*([a-z]{0,4}-?\d{1,4})", listing_n, flags=re.I)}
        if listing_card_nums and card_no.replace("#", "").strip().lower() not in listing_card_nums:
            conflicts.append("Bildhypotesens kortnummer verkar avvika från kortnumret i annonstexten")

    conf = float(result.get("overall_confidence") or 0)
    if conf < 0.55:
        status = "Låg säkerhet – verifiera manuellt"
    elif conflicts:
        status = "Konflikt – verifiera innan analys"
    elif discoveries:
        status = "Möjlig visuell edge"
    else:
        status = "Ingen tydlig ny information"

    return {
        "status": status,
        "discoveries": discoveries[:10],
        "conflicts": conflicts[:6],
        "confidence": round(conf * 100, 1),
        "identity": visual_identity_completeness(result),
        "safe_for_valuation": False,
    }


def analyze_listing_images(item: dict, *, model: str = "gpt-5.4-mini", max_images: int = 4) -> dict:
    """Call OpenAI vision only when explicitly requested by the user.

    Analyses multiple listing photos together so front/back and close-ups can
    corroborate each other. Returns hypotheses only; valuation fields are never
    accepted or returned.
    """
    urls = list(dict.fromkeys(str(x) for x in (item.get("image_urls") or []) if x))[:max_images]
    if not urls:
        return {"success": False, "error": "Ingen annonsbild finns sparad för objektet."}

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "OPENAI_API_KEY saknas. Bildgranskningen kan fortfarande användas som granskningskö, men automatisk bildtolkning kräver API-nyckel.",
        }

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        content: list[dict] = [{
            "type": "input_text",
            "text": json.dumps({
                "listing_title": item.get("titel", ""),
                "listing_raw_text": item.get("raw_text", ""),
                "image_count": len(urls),
                "instruction": (
                    "Granska bilderna som en gemensam fotoserie. Avgör vilka som visar fram-/baksida eller närbild, "
                    "och använd läsbar text på kortet som primärt visuellt bevis. Annonstexten är kontext, inte facit."
                ),
            }, ensure_ascii=False),
        }]
        for idx, url in enumerate(urls, start=1):
            content.append({"type": "input_text", "text": f"Annonsbild {idx} av {len(urls)}:"})
            content.append({"type": "input_image", "image_url": url})

        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
                {"role": "user", "content": content},
            ],
            text={"format": {"type": "json_schema", "name": "visual_card_detective", "schema": response_schema(), "strict": True}},
        )
        if not getattr(response, "output_text", None):
            return {"success": False, "error": "Bildmodellen returnerade inget tolkningsbart svar."}
        parsed = json.loads(response.output_text)
        comparison = compare_visual_to_listing(parsed, item.get("titel", ""), item.get("raw_text", ""))
        return {
            "success": True,
            "model": model,
            "images_analyzed": len(urls),
            "findings": parsed,
            "comparison": comparison,
            "identity": comparison.get("identity", visual_identity_completeness(parsed)),
        }
    except Exception as exc:
        return {"success": False, "error": f"Bildanalysen misslyckades: {exc}"}
