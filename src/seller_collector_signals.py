"""Title-level collector signals used only to prioritize seller inventory research.

These signals never create a BUY decision and never count as SOLD evidence. They
help surface listings whose wording suggests card-specific value drivers so the
normal analyser can inspect them before ordinary base cards.
"""
from __future__ import annotations

import re

_FALSE_AUTO = re.compile(r"\b(signature\s*style|silver\s*script|facsimile|facsimile\s*signature|printed\s*signature|pre[- ]?printed\s*signature)\b", re.I)


def collector_signals(item: dict) -> dict:
    title = str(item.get("titel") or item.get("title") or "").strip()
    text = title.casefold()
    signals: list[tuple[str, int]] = []

    def add(name: str, weight: int, condition: bool):
        if condition:
            signals.append((name, weight))

    add("one_of_one", 24, bool(re.search(r"(?:\b1\s*/\s*1\b|\bone[- ]of[- ]one\b)", text)))
    add("serial_numbered", 18, bool(re.search(
        r"(?:\b\d{1,4}\s*)?/\s*(?:5|10|15|20|25|49|50|75|99|100|199|299|499)\b",
        text,
    )) or "numbered" in text or "numrerad" in text)

    explicit_auto = bool(re.search(r"\b(?:autograph(?:ed)?|auto|on[- ]card\s+auto|hard[- ]signed)\b", text))
    add("autograph", 17, explicit_auto and not _FALSE_AUTO.search(text))
    add("patch_relic", 15, bool(re.search(r"\b(?:patch|relic|memorabilia|jersey|game[- ]used|game[- ]worn)\b", text)))
    add("case_hit_ssp", 17, bool(re.search(r"\b(?:ssp|super\s+short\s+print|case\s+hit)\b", text)))
    add("premium_insert", 15, bool(re.search(r"\b(?:downtown|kaboom|color\s+blast|colour\s+blast|stained\s+glass|blank\s+slate)\b", text)))
    add("rookie", 11, bool(re.search(r"\b(?:rookie|rc|young\s+guns?|future\s+watch)\b", text)))
    add("premium_parallel", 11, bool(re.search(r"\b(?:parallel|refractor|prizm|x-fractor|atomic|gold\s+vinyl|cracked\s+ice|red\s+outburst|exclusives?)\b", text)))
    add("error_variation", 14, bool(re.search(r"\b(?:error|misprint|printing\s+error|variation|variant|wrong\s+back|blank\s+back)\b", text)))
    add("short_print", 10, bool(re.search(r"\bshort\s+print\b", text)))

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
