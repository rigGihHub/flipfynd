"""Premium Comp Hunter for FlipFynd.

Keeps premium cards (auto/patch/low serial/named parallel) from inheriting a
market value from broad same-player comps.  The module only classifies already
observed sold evidence and builds narrow search targets; it never invents a
price.
"""
from __future__ import annotations

import re
from typing import Any, Iterable
from urllib.parse import quote_plus

from src.card_parser import parse_card_features


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _same(a: object, b: object) -> bool:
    aa, bb = _norm(a), _norm(b)
    return bool(aa and bb and aa == bb)


def _features_from_detail(detail: dict) -> dict[str, Any]:
    title = str(detail.get("title") or detail.get("titel") or "")
    raw = str(detail.get("raw_text") or "")
    f = parse_card_features(f"{title} {raw}")
    # Keep explicit structured values if the comp source happens to contain them.
    for key in ("player_name", "set_name", "season", "year", "card_number", "parallel", "grade", "grading_company"):
        if detail.get(key) not in (None, ""):
            f[key] = detail.get(key)
    if detail.get("serial_denominator") not in (None, ""):
        try:
            f["serial_number"] = int(detail["serial_denominator"])
        except (TypeError, ValueError):
            pass
    return f


def is_premium_identity(features: dict) -> bool:
    return bool(
        features.get("is_auto")
        or features.get("is_patch")
        or features.get("is_jersey")
        or features.get("is_low_serial")
        or features.get("is_1of1")
        or features.get("parallel")
    )


def build_premium_query(features: dict) -> str:
    parts: list[str] = []
    player = features.get("player_name")
    if player:
        parts.append(str(player))
    season = features.get("season") or features.get("year")
    if season:
        parts.append(str(season))
    set_name = features.get("set_name")
    if set_name:
        parts.append(str(set_name))
    card_number = features.get("card_number")
    if card_number:
        text = str(card_number)
        parts.append(text if text.startswith("#") else f"#{text}")
    parallel = features.get("parallel")
    if parallel:
        parts.append(str(parallel))
    if features.get("is_auto"):
        parts.append("autograph")
    if features.get("is_patch") or features.get("is_jersey"):
        parts.append("patch")
    serial = features.get("serial_number")
    if serial:
        parts.append(f"/{serial}")
    # preserve order + dedupe
    seen, out = set(), []
    for part in parts:
        key = _norm(part)
        if key and key not in seen:
            seen.add(key)
            out.append(str(part))
    return " ".join(out)


def _classify(features: dict, detail: dict) -> dict[str, Any]:
    comp = _features_from_detail(detail)
    missing: list[str] = []
    conflicts: list[str] = []
    matches: list[str] = []

    raw_title_norm = _norm(detail.get("title") or detail.get("titel") or "")

    def require_equal(key: str, label: str) -> None:
        target = features.get(key)
        if target in (None, ""):
            return
        observed = comp.get(key)
        if observed in (None, ""):
            # Alphanumeric checklist numbers are not always parsed by the generic
            # title parser. Exact textual presence is still useful evidence.
            target_norm = _norm(target)
            if key in {"card_number", "parallel"} and target_norm and target_norm in raw_title_norm:
                matches.append(label)
            else:
                missing.append(label)
        elif _same(target, observed):
            matches.append(label)
        else:
            conflicts.append(label)

    # Player is always essential when known.
    require_equal("player_name", "spelare")
    # Product/program identity is critical for premium cards.
    require_equal("set_name", "set/program")
    require_equal("season", "säsong")
    require_equal("card_number", "kortnummer")
    require_equal("parallel", "variant/parallel")

    if features.get("is_auto"):
        if comp.get("is_auto"):
            matches.append("autograf")
        else:
            missing.append("autograf")
    if features.get("is_patch") or features.get("is_jersey"):
        if comp.get("is_patch") or comp.get("is_jersey"):
            matches.append("patch/relic")
        else:
            missing.append("patch/relic")

    target_serial = features.get("serial_number")
    comp_serial = comp.get("serial_number")
    if target_serial:
        if not comp_serial:
            missing.append("numrering")
        elif int(target_serial) == int(comp_serial):
            matches.append("numrering")
        else:
            conflicts.append("numrering")

    # Explicit premium trait conflicts reject. Missing data is not treated as proof.
    if conflicts:
        tier = "REJECTED"
    else:
        essential = ["spelare"]
        if features.get("set_name"):
            essential.append("set/program")
        if features.get("is_auto"):
            essential.append("autograf")
        if features.get("is_patch") or features.get("is_jersey"):
            essential.append("patch/relic")
        if features.get("parallel"):
            essential.append("variant/parallel")
        if target_serial:
            essential.append("numrering")
        if features.get("card_number"):
            essential.append("kortnummer")

        essential_ok = all(label in matches for label in essential)
        # One non-essential missing field (usually season) is tolerable; premium traits are not.
        if essential_ok and len(missing) <= 1:
            tier = "EXACT_PREMIUM"
        elif "spelare" in matches and any(x in matches for x in ("autograf", "patch/relic", "set/program")):
            tier = "NEAR_PREMIUM"
        else:
            tier = "INSUFFICIENT"

    return {
        "tier": tier,
        "matches": matches,
        "missing": missing,
        "conflicts": conflicts,
        "title": detail.get("title") or detail.get("titel") or "",
        "price": detail.get("sold_price") if detail.get("sold_price") not in (None, "") else detail.get("price"),
        "url": detail.get("url") or detail.get("lank"),
        "date": detail.get("date") or detail.get("sold_at") or detail.get("sold_date"),
        "platform": detail.get("platform") or detail.get("source") or "historik",
    }


def hunt_premium_comps(features: dict, comparable_details: Iterable[dict] | None = None) -> dict[str, Any]:
    premium = is_premium_identity(features)
    query = build_premium_query(features)
    if not premium:
        return {
            "active": False,
            "status": "Inte ett premiumkort",
            "exact_count": 0,
            "near_count": 0,
            "exact": [],
            "near": [],
            "rejected": [],
            "query": query,
            "search_targets": [],
            "safe_for_valuation": False,
        }

    buckets = {"EXACT_PREMIUM": [], "NEAR_PREMIUM": [], "INSUFFICIENT": [], "REJECTED": []}
    for detail in list(comparable_details or []):
        if str(detail.get("market_state") or "").casefold() != "sold":
            continue
        classified = _classify(features, detail)
        buckets[classified["tier"]].append(classified)

    exact = buckets["EXACT_PREMIUM"]
    near = buckets["NEAR_PREMIUM"]
    rejected = buckets["REJECTED"]
    if len(exact) >= 2:
        status = "Premiumvärdering har minst två exakta sold comps"
    elif exact:
        status = "En exakt premium-comp hittad – minst två behövs"
    elif near:
        status = "Närliggande premium-comps finns, men inga exakta"
    else:
        status = "Inga exakta premium-comps i lokal historik"

    targets = []
    if query:
        q = quote_plus(query)
        targets = [
            {
                "platform": "eBay sold",
                "url": f"https://www.ebay.com/sch/i.html?_nkw={q}&LH_Sold=1&LH_Complete=1",
                "note": "Verifiera exakt spelare, set/program, variant, kortnummer och premiumegenskap.",
            },
            {
                "platform": "Tradera",
                "url": f"https://www.tradera.com/search?q={q}",
                "note": "Aktiva annonser är utbud, inte verifierade försäljningar.",
            },
        ]

    return {
        "active": True,
        "status": status,
        "exact_count": len(exact),
        "near_count": len(near),
        "insufficient_count": len(buckets["INSUFFICIENT"]),
        "rejected_count": len(rejected),
        "exact": exact[:10],
        "near": near[:10],
        "rejected": rejected[:10],
        "query": query,
        "search_targets": targets,
        "safe_for_valuation": len(exact) >= 2,
        "note": "Premium Comp Hunter skapar inga priser. Den avgör bara om sålda jämförelser verkligen matchar premiumkortets identitet.",
    }
