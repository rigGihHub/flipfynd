"""Seller-inventory guard for sports-card discovery."""
from __future__ import annotations

import re

_BLOCK_PATTERNS = (
    r"\bserie\s*nytt\b",
    r"\bserietidning(?:ar)?\b",
    r"\bcomic(?:s)?\b",
    r"\bmagasin\b",
    r"\b\w*magasin\w*\b",
    r"\btidning(?:ar)?\b",
    r"\b\w*tidning(?:ar)?\b",
    r"\bbok\b",
    r"\bbook\b",
    r"\balbum\b",
    r"\bklisterm(?:a|ä)rkesalbum\b",
    r"\bsticker\s*album\b",
    r"\bfigur(?:er)?\b",
    r"\bfigure\b",
    r"\bposter\b",
    r"\bpussel\b",
    r"\bmynt\b",
    r"\bcoin\b",
)
_CARD_HINTS = (
    "card", "kort", "rookie", "rc", "upper deck", "topps", "panini", "o-pee-chee",
    "opc", "fleer", "score", "donruss", "prizm", "select", "finest", "bowman",
    "autograph", "auto", "patch", "jersey", "parallel", "refractor", "young guns",
)


def seller_item_domain_check(item: dict, sport: str = "hockey") -> dict:
    title = str(item.get("titel") or item.get("title") or "").strip()
    text = title.casefold()
    for pattern in _BLOCK_PATTERNS:
        if re.search(pattern, text, re.I):
            return {"allowed": False, "reason": "NOT_A_TRADING_CARD", "title": title}

    # Explicit category metadata can override weak title ambiguity.
    category_text = " ".join(str(item.get(k) or "") for k in ("category_name", "category", "breadcrumb", "path")).casefold()
    if any(word in category_text for word in ("serietid", "böcker", "books", "magasin", "comics")):
        return {"allowed": False, "reason": "NON_CARD_CATEGORY", "title": title}

    # Do not reject terse listings solely because they lack a card word; many real
    # card listings are just year + player. The guard is intentionally asymmetric:
    # strong non-card evidence blocks, uncertainty remains analyzable.
    return {"allowed": True, "reason": "NO_NON_CARD_EVIDENCE", "title": title}
