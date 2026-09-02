"""Exact Comp Hunter for FlipFynd.

Builds narrow, auditable comp searches from a corroborated card identity and
classifies local sold-history records as exact, near or rejected. It never
creates prices: it only organises evidence and search targets.
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


def _compatible_set(a: object, b: object) -> bool:
    aa, bb = _norm(a), _norm(b)
    if not aa or not bb:
        return False
    if aa == bb or aa in bb or bb in aa:
        return True
    links = [
        ({"upper deck series 1", "upper deck series one"}, {"young guns"}),
        ({"sp authentic"}, {"future watch", "future watch autograph"}),
        ({"o pee chee platinum", "opc platinum"}, {"marquee rookie"}),
    ]
    return any((aa in products and bb in programs) or (bb in products and aa in programs) for products, programs in links)


def _record_features(record: dict) -> dict[str, Any]:
    title = str(record.get("titel") or record.get("title") or "")
    raw = str(record.get("raw_text") or "")
    f = parse_card_features(f"{title} {raw}")
    aliases = {
        "player_name": ("player_name", "player"),
        "set_name": ("set_name", "set", "product"),
        "season": ("season", "year"),
        "card_number": ("card_number", "checklist_number"),
        "parallel": ("parallel", "variant"),
        "grading_company": ("grading_company",),
        "grade": ("grade",),
    }
    for target, keys in aliases.items():
        for key in keys:
            if record.get(key) not in (None, ""):
                f[target] = record.get(key)
                break
    if record.get("serial_denominator") not in (None, ""):
        try:
            f["serial_denominator"] = int(record["serial_denominator"])
        except (TypeError, ValueError):
            pass
    elif f.get("serial_number"):
        f["serial_denominator"] = f.get("serial_number")
    return f


def build_exact_query(identity: dict[str, Any]) -> str:
    """Create a narrow human-readable search query from structured identity."""
    parts: list[str] = []
    for key in ("player_name", "season", "set_name", "card_number", "parallel"):
        value = identity.get(key)
        if value not in (None, ""):
            text = str(value).strip()
            if key == "card_number" and not text.startswith("#"):
                text = f"#{text}"
            parts.append(text)
    serial_den = identity.get("serial_denominator")
    if serial_den:
        parts.append(f"/{serial_den}")
    if identity.get("is_auto"):
        parts.append("auto")
    if identity.get("is_patch"):
        parts.append("patch")
    if identity.get("grading_company"):
        grade = str(identity.get("grade") or "").strip()
        parts.append((str(identity["grading_company"]) + (" " + grade if grade else "")).strip())
    # Preserve order but remove duplicates.
    seen = set()
    out = []
    for part in parts:
        key = _norm(part)
        if key and key not in seen:
            seen.add(key)
            out.append(part)
    return " ".join(out)


def build_search_targets(identity: dict[str, Any]) -> list[dict[str, str]]:
    query = build_exact_query(identity)
    if not query:
        return []
    q = quote_plus(query)
    # Search links do not assert that a result is sold or comparable. The user
    # must still verify market state and identity.
    return [
        {
            "platform": "Tradera",
            "query": query,
            "url": f"https://www.tradera.com/search?q={q}",
            "note": "Aktiva annonser – använd som utbud/asking, inte som såld comp.",
        },
        {
            "platform": "eBay sold",
            "query": query,
            "url": f"https://www.ebay.com/sch/i.html?_nkw={q}&LH_Sold=1&LH_Complete=1",
            "note": "Kontrollera att avslutet verkligen gäller exakt samma kort och faktiskt såld vara.",
        },
    ]


def classify_comp(identity: dict[str, Any], record: dict) -> dict[str, Any]:
    """Classify an observed record without letting a near match masquerade as exact."""
    rf = _record_features(record)
    exact_matches: list[str] = []
    missing: list[str] = []
    conflicts: list[str] = []

    fields = [
        ("player_name", "spelare", True),
        ("set_name", "set/produkt", True),
        ("season", "säsong/år", False),
        ("card_number", "kortnummer", False),
        ("parallel", "parallel", False),
        ("grading_company", "grading", False),
        ("grade", "grade", False),
    ]
    for key, label, set_compat in fields:
        iv, rv = identity.get(key), rf.get(key)
        if iv in (None, ""):
            continue
        if rv in (None, ""):
            missing.append(label)
            continue
        match = _compatible_set(iv, rv) if set_compat and key == "set_name" else _same(iv, rv)
        if match:
            exact_matches.append(label)
        else:
            conflicts.append(label)

    iden_den = identity.get("serial_denominator")
    rec_den = rf.get("serial_denominator")
    if iden_den:
        if not rec_den:
            missing.append("serienämnare")
        elif int(iden_den) == int(rec_den):
            exact_matches.append("serienämnare")
        else:
            conflicts.append("serienämnare")

    for key, label, record_keys in [
        ("is_auto", "autograf", ("is_auto",)),
        ("is_patch", "patch/relic", ("is_patch", "is_jersey")),
    ]:
        if identity.get(key):
            if any(rf.get(k) for k in record_keys):
                exact_matches.append(label)
            else:
                missing.append(label)

    # Hard identity conflicts always reject.
    if conflicts:
        tier = "REJECTED"
    else:
        core_required = [k for k in ("player_name", "card_number") if identity.get(k)]
        core_ok = all(
            ("spelare" if k == "player_name" else "kortnummer") in exact_matches
            for k in core_required
        )
        set_or_season_ok = (
            (not identity.get("set_name") or "set/produkt" in exact_matches)
            or (not identity.get("season") or "säsong/år" in exact_matches)
        )
        variant_fields = [
            ("parallel", "parallel"),
            ("serial_denominator", "serienämnare"),
            ("grading_company", "grading"),
            ("grade", "grade"),
        ]
        variant_known_ok = all(not identity.get(k) or label in exact_matches for k, label in variant_fields)
        if core_ok and set_or_season_ok and variant_known_ok and len(missing) <= 1:
            tier = "EXACT"
        elif core_ok and len(exact_matches) >= 2:
            tier = "NEAR"
        else:
            tier = "WEAK"

    sold = bool(record.get("sold_price") not in (None, "") or str(record.get("market_state") or "").casefold() == "sold")
    return {
        "tier": tier,
        "sold": sold,
        "matches": exact_matches,
        "missing": missing,
        "conflicts": conflicts,
        "price": record.get("sold_price") if record.get("sold_price") not in (None, "") else record.get("price"),
        "platform": record.get("platform") or record.get("source") or "historik",
        "url": record.get("url") or record.get("lank"),
        "title": record.get("titel") or record.get("title") or "",
        "sold_at": record.get("sold_at") or record.get("sold_date") or record.get("date"),
    }


def hunt_exact_comps(identity_candidate: dict, observed_records: Iterable[dict] | None = None) -> dict:
    """Return exact/near/rejected local comps and external search targets.

    Only a candidate marked verified_identity may unlock an exact hunt. This
    keeps image-only guesses out of the comp engine.
    """
    identity = dict(identity_candidate.get("identity_fields") or {})
    if not identity_candidate.get("verified_identity"):
        return {
            "status": "Låst – identiteten är inte verifierad",
            "unlocked": False,
            "query": build_exact_query(identity),
            "exact": [], "near": [], "weak": [], "rejected": [],
            "search_targets": [],
            "note": "Bildhypoteser får inte starta exact-comp-värdering utan oberoende identitetsstöd.",
        }
    if not identity.get("player_name") or not identity.get("card_number"):
        return {
            "status": "Låst – spelare och kortnummer krävs",
            "unlocked": False,
            "query": build_exact_query(identity),
            "exact": [], "near": [], "weak": [], "rejected": [],
            "search_targets": [],
            "note": "Exakt comp-sökning kräver minst spelare och kortnummer.",
        }

    buckets = {"EXACT": [], "NEAR": [], "WEAK": [], "REJECTED": []}
    for record in list(observed_records or []):
        c = classify_comp(identity, record)
        buckets[c["tier"]].append(c)

    # Exact valuation evidence must be sold; active/unknown records are kept as
    # search context only and never promoted to sold evidence.
    exact_sold = [x for x in buckets["EXACT"] if x.get("sold")]
    near_sold = [x for x in buckets["NEAR"] if x.get("sold")]
    status = "Exakta verifierade comps hittade" if exact_sold else "Ingen exakt såld comp i lokal historik"
    return {
        "status": status,
        "unlocked": True,
        "query": build_exact_query(identity),
        "exact": exact_sold,
        "near": near_sold,
        "weak": buckets["WEAK"],
        "rejected": buckets["REJECTED"],
        "search_targets": build_search_targets(identity),
        "exact_sold_count": len(exact_sold),
        "near_sold_count": len(near_sold),
        "note": "Exact Comp Hunter organiserar bevis. Den ändrar inte marknadsvärde eller köpbeslut automatiskt.",
    }
