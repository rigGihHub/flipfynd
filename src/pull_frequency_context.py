"""Normalize published pull odds into pack / box / case context.

This module never estimates price. It only translates source-backed pull frequency
into a more intuitive hobby context when enough product-format metadata exists.
If box/case configuration is unknown, the raw published odds are preserved and no
box/case conversion is invented.
"""
from __future__ import annotations

import math
import re
from typing import Any


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def parse_published_odds(value: Any) -> dict[str, Any] | None:
    """Parse odds such as ``1:144 Hobby`` or ``1 per case`` conservatively."""
    text = str(value or "").strip()
    if not text:
        return None
    n = _norm(text)

    m = re.search(r"1\s*[:/]\s*([0-9][0-9,]*)", text)
    if m:
        try:
            den = int(m.group(1).replace(",", ""))
        except ValueError:
            return None
        if den <= 0:
            return None
        unit = "pack"
        if "box" in n:
            unit = "box"
        elif "case" in n:
            unit = "case"
        return {"numerator": 1, "denominator": den, "unit": unit, "raw": text}

    # Wording such as "1 per box", "1 per 2 cases".
    m = re.search(r"\b1\s+(?:per|every)\s+([0-9]+)?\s*(pack|packs|box|boxes|case|cases)\b", n)
    if m:
        den = int(m.group(1) or 1)
        unit_raw = m.group(2)
        unit = "pack" if unit_raw.startswith("pack") else "box" if unit_raw.startswith("box") else "case"
        return {"numerator": 1, "denominator": den, "unit": unit, "raw": text}
    return None


def _positive_int(value: Any) -> int | None:
    try:
        iv = int(value)
    except (TypeError, ValueError):
        return None
    return iv if iv > 0 else None


def contextualize_pull_frequency(signal: dict[str, Any]) -> dict[str, Any]:
    """Return source-aware frequency context without inventing product configuration."""
    row = signal or {}
    raw = row.get("pull_odds") or row.get("published_odds")
    parsed = parse_published_odds(raw)
    if not parsed:
        return {
            "raw_odds": raw,
            "parsed": False,
            "unit": None,
            "denominator": None,
            "packs_per_hit": None,
            "boxes_per_hit": None,
            "cases_per_hit": None,
            "frequency_band": None,
            "frequency_label": None,
            "configuration_complete": False,
            "note": "Inga tolkningsbara publicerade odds.",
        }

    unit = parsed["unit"]
    den = int(parsed["denominator"])
    packs_per_box = _positive_int(row.get("packs_per_box"))
    boxes_per_case = _positive_int(row.get("boxes_per_case"))

    packs_per_hit: float | None = None
    boxes_per_hit: float | None = None
    cases_per_hit: float | None = None

    if unit == "pack":
        packs_per_hit = float(den)
        if packs_per_box:
            boxes_per_hit = packs_per_hit / packs_per_box
            if boxes_per_case:
                cases_per_hit = boxes_per_hit / boxes_per_case
    elif unit == "box":
        boxes_per_hit = float(den)
        if boxes_per_case:
            cases_per_hit = boxes_per_hit / boxes_per_case
        if packs_per_box:
            packs_per_hit = boxes_per_hit * packs_per_box
    elif unit == "case":
        cases_per_hit = float(den)
        if boxes_per_case:
            boxes_per_hit = cases_per_hit * boxes_per_case
            if packs_per_box:
                packs_per_hit = boxes_per_hit * packs_per_box

    # Banding is based on the strongest context actually known. Thresholds are
    # descriptive analysis buckets, not claims that a card is valuable.
    band = None
    label = None
    if cases_per_hit is not None:
        if cases_per_hit >= 5:
            band, label = "multi_case", f"cirka 1 per {cases_per_hit:.1f} case"
        elif cases_per_hit >= 1:
            band, label = "case_level", f"cirka 1 per {cases_per_hit:.1f} case"
        elif boxes_per_hit is not None and boxes_per_hit >= 1:
            band, label = "box_level", f"cirka 1 per {boxes_per_hit:.1f} box"
        else:
            band, label = "sub_box", "oftare än ungefär 1 per box"
    elif boxes_per_hit is not None:
        if boxes_per_hit >= 12:
            band, label = "rare_box_level", f"cirka 1 per {boxes_per_hit:.1f} box"
        elif boxes_per_hit >= 1:
            band, label = "box_level", f"cirka 1 per {boxes_per_hit:.1f} box"
        else:
            band, label = "sub_box", "oftare än ungefär 1 per box"
    elif unit == "case":
        band, label = ("multi_case" if den >= 5 else "case_level"), f"1 per {den} case"
    elif unit == "box":
        band, label = ("rare_box_level" if den >= 12 else "box_level"), f"1 per {den} box"
    else:
        # No product configuration: preserve pack context only.
        if den <= 12:
            band, label = "pack_common", f"1 per {den} pack"
        elif den <= 96:
            band, label = "pack_uncommon", f"1 per {den} pack"
        elif den <= 576:
            band, label = "pack_rare", f"1 per {den} pack"
        else:
            band, label = "pack_extreme", f"1 per {den} pack"

    return {
        "raw_odds": raw,
        "parsed": True,
        "unit": unit,
        "denominator": den,
        "packs_per_box": packs_per_box,
        "boxes_per_case": boxes_per_case,
        "packs_per_hit": packs_per_hit,
        "boxes_per_hit": boxes_per_hit,
        "cases_per_hit": cases_per_hit,
        "frequency_band": band,
        "frequency_label": label,
        "configuration_complete": bool(packs_per_box and boxes_per_case),
        "note": (
            "Box/case-kontext bygger endast på explicit produktkonfiguration i kunskapsbasen. "
            "Saknas den visas bara de publicerade odds som faktiskt är kända."
        ),
    }
