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
Du är en försiktig bildgranskare för samlarkort (hockey och fotboll).
Din uppgift är endast att beskriva visuella ledtrådar som faktiskt går att se i bilden.

Absoluta regler:
- Gissa aldrig ett kortnummer, serienummer, parallel, rookie-status, autograf, patch/relic, set, år eller spelare.
- Om detaljen inte går att läsa tydligt: använd null/unknown och låg confidence.
- En tryckt/faksimil-signatur får inte kallas autograf om det inte finns tydligt visuellt stöd.
- Ett glansigt/färgat kort får inte automatiskt kallas en specifik parallel.
- Svara inte med pris, marknadsvärde, ROI, vinst eller köprekommendation.
- Svara endast med JSON enligt schemat.
""".strip()


def response_schema() -> dict[str, Any]:
    nullable_string = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    nullable_int = {"anyOf": [{"type": "integer"}, {"type": "null"}]}
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "player_name": nullable_string,
            "set_or_product": nullable_string,
            "season_or_year": nullable_string,
            "card_number": nullable_string,
            "serial_numerator": nullable_int,
            "serial_denominator": nullable_int,
            "parallel_or_variant": nullable_string,
            "rookie_marker_visible": {"type": "string", "enum": ["yes", "no", "unknown"]},
            "autograph_visible": {"type": "string", "enum": ["yes", "no", "unknown"]},
            "relic_or_patch_visible": {"type": "string", "enum": ["yes", "no", "unknown"]},
            "grading_company": nullable_string,
            "grade": nullable_string,
            "overall_confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "needs_back_image": {"type": "boolean"},
            "visual_clues": {"type": "array", "items": {"type": "string"}},
            "uncertainties": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "player_name", "set_or_product", "season_or_year", "card_number",
            "serial_numerator", "serial_denominator", "parallel_or_variant",
            "rookie_marker_visible", "autograph_visible", "relic_or_patch_visible",
            "grading_company", "grade", "overall_confidence", "needs_back_image",
            "visual_clues", "uncertainties",
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


def compare_visual_to_listing(result: dict, title: str = "", raw_text: str = "") -> dict:
    """Compare visual hypotheses with listing text without promoting them to facts."""
    title_n = _norm(title)
    listing_n = _norm(f"{title} {raw_text}")
    discoveries: list[str] = []
    conflicts: list[str] = []

    fields = [
        ("spelare", result.get("player_name")),
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

    # Explicit yes signals are discoveries only if the listing does not already say so.
    yes_terms = [
        ("rookie/RC-markering", result.get("rookie_marker_visible") == "yes", ("rookie", " rc ", "young guns", "rated rookie")),
        ("autograf", result.get("autograph_visible") == "yes", ("auto", "autograf", "autograph", "signerad")),
        ("patch/relic", result.get("relic_or_patch_visible") == "yes", ("patch", "relic", "jersey", "memorabilia")),
    ]
    padded = f" {listing_n} "
    for label, is_yes, terms in yes_terms:
        if is_yes and not any(term in padded for term in terms):
            discoveries.append(f"Bilden antyder {label}, men annonstexten nämner inte det")

    # Conservative conflict check: only flag when listing explicitly carries a
    # different serial denominator/card number pattern.
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
        "discoveries": discoveries[:8],
        "conflicts": conflicts[:5],
        "confidence": round(conf * 100, 1),
        "safe_for_valuation": False,
    }


def analyze_listing_images(item: dict, *, model: str = "gpt-5.4-mini", max_images: int = 2) -> dict:
    """Call OpenAI vision only when explicitly requested by the user.

    Returns hypotheses only. No valuation fields are accepted or returned.
    """
    urls = [str(x) for x in (item.get("image_urls") or []) if x][:max_images]
    if not urls:
        return {"success": False, "error": "Ingen annonsbild finns sparad för objektet."}

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "OPENAI_API_KEY saknas. Visual Card Detective kan fortfarande användas som granskningskö, men automatisk bildtolkning kräver API-nyckel.",
        }

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        content: list[dict] = [{
            "type": "input_text",
            "text": json.dumps({
                "listing_title": item.get("titel", ""),
                "listing_raw_text": item.get("raw_text", ""),
                "instruction": "Granska endast synliga kortdetaljer. Annonstexten är kontext, inte facit.",
            }, ensure_ascii=False),
        }]
        for url in urls:
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
        }
    except Exception as exc:
        return {"success": False, "error": f"Bildanalysen misslyckades: {exc}"}
