"""Title-level collector signals used only to prioritize seller inventory research.

These signals never create a BUY decision and never count as SOLD evidence. They
help surface listings whose wording suggests card-specific value drivers so the
normal analyser can inspect them before ordinary base cards.
"""
from __future__ import annotations

import re

from src.card_parser import has_relic_material_evidence

_FALSE_AUTO = re.compile(r"\b(signature\s*style|silver\s*script|facsimile|facsimile\s*signature|printed\s*signature|pre[- ]?printed\s*signature)\b", re.I)


def _has_serial_numbering(text: str) -> bool:
    if "numbered" in text or "numrerad" in text:
        return True
    # Remove explicit seasons before looking for print-run fractions. Without
    # this, e.g. 2024/25 was interpreted as a card numbered to /25.
    serial_text = re.sub(
        r"\b(?:19|20)\d{2}\s*[-/]\s*(?:(?:19|20)?\d{2})\b",
        " ",
        text,
    )
    serial_text = re.sub(
        r"(?<!\d)(\d{2})\s*[-/]\s*(\d{2})(?!\d)",
        lambda match: " " if (int(match.group(2)) - int(match.group(1))) % 100 == 1 else match.group(0),
        serial_text,
    )
    pattern = re.compile(r"(?<![#\d])(\d{1,4})\s*/\s*(5|10|15|20|25|49|50|75|99|100|199|299|499)\b")
    for match in pattern.finditer(serial_text):
        numerator, denominator = int(match.group(1)), int(match.group(2))
        # 2024/2025 and 24/25 are seasons, not print runs. A leading # also
        # denotes a checklist card number and is excluded by the regex.
        if denominator == numerator + 1 and (numerator >= 19 or numerator >= 1900):
            continue
        return True
    return False


def collector_signals(item: dict) -> dict:
    title = str(item.get("titel") or item.get("title") or "").strip()
    text = title.casefold()
    signals: list[tuple[str, int]] = []

    def add(name: str, weight: int, condition: bool):
        if condition:
            signals.append((name, weight))

    add("one_of_one", 24, bool(re.search(r"(?:\b1\s*/\s*1\b|\bone[- ]of[- ]one\b)", text)))
    add("serial_numbered", 18, _has_serial_numbering(text))

    explicit_auto = bool(re.search(r"\b(?:autograph(?:ed)?|auto|on[- ]card\s+auto|hard[- ]signed)\b", text))
    add("autograph", 17, explicit_auto and not _FALSE_AUTO.search(text))
    add("patch_relic", 15, has_relic_material_evidence(text))
    add("case_hit_ssp", 17, bool(re.search(r"\b(?:ssp|super\s+short\s+print|case\s+hit)\b", text)))
    add("premium_insert", 15, bool(re.search(r"\b(?:downtown|kaboom|color\s+blast|colour\s+blast|stained\s+glass|blank\s+slate)\b", text)))
    add("rookie", 11, bool(re.search(r"\b(?:rookie|rc|young\s+guns?|future\s+watch)\b", text)))
    add("premium_parallel", 11, bool(re.search(r"\b(?:parallel|refractor|prizm|x-fractor|atomic|gold\s+vinyl|cracked\s+ice|red\s+outburst|exclusives?)\b", text)))
    add("error_variation", 14, bool(re.search(r"\b(?:error|misprint|printing\s+error|variation|variant|wrong\s+back|blank\s+back)\b", text)))
    add("short_print", 10, bool(re.search(r"\bshort\s+print\b", text)))
    add("printing_plate", 20, bool(re.search(r"\b(?:printing|tryck)\s+plate\b", text)))
    add("buyback", 16, bool(re.search(r"\bbuyback\b", text)))
    add("photo_variation", 14, bool(re.search(r"\b(?:photo|image|bild)\s+variation\b", text)))
    add("acetate", 10, bool(re.search(r"\bacetate\b", text)))
    add("die_cut", 8, bool(re.search(r"\bdie[- ]?cut\b", text)))

    penalty = 0
    if re.search(r"\b(?:base\s+card|basekort|common|bas\s*kort)\b", text):
        penalty -= 14

    raw = sum(weight for _, weight in signals) + penalty
    score = max(0, min(40, raw))
    return {
        "score": score,
        "signals": [name for name, _ in signals],
        "penalty": penalty,
        "title": title,
    }
