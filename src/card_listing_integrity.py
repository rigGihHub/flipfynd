"""Title-level integrity checks shared by ordinary and seller searches.

The checks prevent non-original or non-single-card products from inheriting
market values from genuine physical cards. They never prove authenticity.
"""
from __future__ import annotations

import re

_HARD_EXCLUSIONS = {
    "digital_card": re.compile(r"\b(?:digital\s+card|digitalt\s+kort|e[- ]?card|nft)\b", re.I),
    "custom_proxy": re.compile(r"\b(?:custom(?:\s+made)?|fan[- ]?made|hemmagjor(?:d|t)|proxy\s+card)\b", re.I),
    "replica_counterfeit": re.compile(r"\b(?:replica|counterfeit|fake\s+card|kopiakort|kopia)\b", re.I),
    "mystery_repack": re.compile(r"\b(?:mystery\s+(?:pack|box)|repack(?:ed)?)\b", re.I),
}
_REPRINT = re.compile(r"\b(?:reprint|reproduction|nytryck|repro)\b", re.I)
_SEALED = re.compile(
    r"\b(?:hobby|retail|blaster|booster|mega)\s+(?:box|pack)|"
    r"(?:sealed|ooppnad|oöppnad)\s+(?:box|pack|paket)|"
    r"(?:box|display)\s+med\s+(?:kort|packs?)\b",
    re.I,
)


def assess_listing_integrity(item_or_title) -> dict:
    if isinstance(item_or_title, dict):
        title = str(item_or_title.get("titel") or item_or_title.get("title") or "")
    else:
        title = str(item_or_title or "")
    hard_reasons = [name for name, pattern in _HARD_EXCLUSIONS.items() if pattern.search(title)]
    if _SEALED.search(title):
        hard_reasons.append("sealed_product")
    reprint = bool(_REPRINT.search(title))
    return {
        "eligible_physical_single_card": not hard_reasons,
        "hard_exclusion_reasons": hard_reasons,
        "reprint_risk": reprint,
        "requires_exact_variant_comps": reprint,
    }
