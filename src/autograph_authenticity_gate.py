"""Conservative autograph authenticity gate.

A visible signature is not equivalent to a certified autograph.  This module
keeps printed/facsimile script parallels and unclear signatures from being
promoted into autograph premiums, comp identities, or buy reasoning.
"""
from __future__ import annotations

import re

PRINTED_SCRIPT_PATTERNS = (
    r"\bsilver\s+script\b",
    r"\bsuper\s+script\b",
    r"\bprinted\s+(?:signature|autograph)\b",
    r"\bfacsimile\b",
    r"\bpre[- ]?printed\s+(?:signature|autograph)\b",
)
CERTIFIED_AUTO_PATTERNS = (
    r"\bcertified\s+autograph\b",
    r"\bcertified\s+auto\b",
    r"\bon[- ]card\s+auto(?:graph)?\b",
    r"\bsticker\s+auto(?:graph)?\b",
    r"\bautograph(?:ed)?\s+card\b",
)


def classify_autograph(*, title: str = "", description: str = "", visual_findings: dict | None = None) -> dict:
    text = re.sub(r"\s+", " ", f"{title} {description}".lower()).strip()
    visual = visual_findings or {}
    auto_type = str(visual.get("autograph_type") or "unknown").lower()
    visible = str(visual.get("autograph_visible") or "unknown").lower()

    if auto_type == "printed_or_facsimile" or any(re.search(p, text) for p in PRINTED_SCRIPT_PATTERNS):
        return {"status": "printed_or_facsimile", "is_certified_autograph": False,
                "label": "Tryckt/faksimil-signatur – ingen verifierad autograf",
                "blocks_autograph_premium": True}
    if auto_type in {"on_card", "sticker"} and visible == "yes":
        return {"status": auto_type, "is_certified_autograph": True,
                "label": "Visuell autografsignal – verifiera mot checklista/certifiering",
                "blocks_autograph_premium": False}
    if any(re.search(p, text) for p in CERTIFIED_AUTO_PATTERNS):
        return {"status": "listing_claim", "is_certified_autograph": False,
                "label": "Annonsen påstår autograf – kräver verifiering",
                "blocks_autograph_premium": True}
    if visible == "yes" or auto_type == "unclear":
        return {"status": "unclear", "is_certified_autograph": False,
                "label": "Signatur synlig/oklar – inte verifierad autograf",
                "blocks_autograph_premium": True}
    return {"status": "none", "is_certified_autograph": False,
            "label": "Ingen verifierad autograf", "blocks_autograph_premium": True}


def safe_visual_is_auto(findings: dict | None) -> bool:
    """Only on-card/sticker visual evidence may enter the auto feature path."""
    f = findings or {}
    return f.get("autograph_visible") == "yes" and f.get("autograph_type") in {"on_card", "sticker"}
