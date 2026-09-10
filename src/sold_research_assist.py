"""Manual sold-research assistance without automated scraping.

Everything here is based on explicit structured identity and user-confirmed sale
evidence. The helpers never infer a sold price, sale state, FX rate or identity.
"""
from __future__ import annotations

from urllib.parse import quote_plus

CORE_FIELDS = ("player_name", "set_name", "season", "card_number")
OPTIONAL_FIELDS = ("parallel", "serial_denominator", "grading_company", "grade")


def build_exact_research_query(identity: dict) -> dict:
    identity = identity or {}
    missing = [field for field in CORE_FIELDS if identity.get(field) in (None, "")]
    if missing:
        return {
            "ready": False,
            "query": None,
            "missing_fields": missing,
            "note": "Exakt research kräver strukturerad spelare, set, säsong och kortnummer.",
        }

    parts = [
        str(identity["player_name"]).strip(),
        str(identity["set_name"]).strip(),
        str(identity["season"]).strip(),
        f"#{str(identity['card_number']).strip()}",
    ]
    for field in OPTIONAL_FIELDS:
        value = identity.get(field)
        if value not in (None, ""):
            parts.append(str(value).strip())

    return {
        "ready": True,
        "query": " ".join(part for part in parts if part),
        "missing_fields": [],
        "note": "Sökfrasen byggs enbart av strukturerad kortidentitet.",
    }


def ebay_sold_search_url(identity: dict) -> str | None:
    query = build_exact_research_query(identity)
    if not query["ready"]:
        return None
    return (
        "https://www.ebay.com/sch/i.html"
        f"?_nkw={quote_plus(query['query'])}&LH_Sold=1&LH_Complete=1"
    )


def build_manual_sold_row(
    identity: dict,
    *,
    sold_price,
    currency,
    source_platform,
    sold_url="",
    sold_at="",
    shipping=None,
    fx_rate_to_sek=None,
    identity_verified=False,
    identity_evidence_source="",
    sale_confirmed=False,
):
    if not sale_confirmed:
        raise ValueError("försäljningen måste vara uttryckligen verifierad innan den kan registreras")

    try:
        price = float(sold_price)
    except (TypeError, ValueError):
        raise ValueError("positivt sålt pris krävs")
    if price <= 0:
        raise ValueError("positivt sålt pris krävs")

    currency = str(currency or "").strip().upper()
    if not currency:
        raise ValueError("valuta krävs")

    source_platform = str(source_platform or "").strip()
    if not source_platform:
        raise ValueError("källa krävs")

    row = {
        "title": build_exact_research_query(identity).get("query") or "Verifierad kortförsäljning",
        "sold_price": price,
        "currency": currency,
        "source_platform": source_platform,
        "sale_status": "sold",
        "sold": True,
    }

    if currency != "SEK":
        if fx_rate_to_sek in (None, ""):
            raise ValueError("annan valuta än SEK kräver explicit fx_rate_to_sek")
        try:
            fx_value = float(fx_rate_to_sek)
        except (TypeError, ValueError):
            raise ValueError("fx_rate_to_sek måste vara ett positivt tal")
        if fx_value <= 0:
            raise ValueError("fx_rate_to_sek måste vara ett positivt tal")
        row["fx_rate_to_sek"] = fx_value

    if sold_url:
        row["url"] = str(sold_url).strip()
    if sold_at:
        row["sold_at"] = str(sold_at).strip()
    if shipping not in (None, ""):
        try:
            shipping_value = float(shipping)
        except (TypeError, ValueError):
            raise ValueError("frakt måste vara ett tal eller lämnas tom")
        if shipping_value < 0:
            raise ValueError("frakt kan inte vara negativ")
        row["shipping"] = shipping_value

    for field in CORE_FIELDS + OPTIONAL_FIELDS:
        value = (identity or {}).get(field)
        if value not in (None, ""):
            row[field] = value

    row["identity_verified"] = bool(identity_verified)
    if identity_evidence_source:
        row["identity_evidence_source"] = str(identity_evidence_source).strip()

    return row


def build_quick_capture_defaults(identity: dict, source_platform: str = "eBay") -> dict:
    """Return safe form defaults only; never invent sale facts."""
    query = build_exact_research_query(identity)
    return {
        "title": query.get("query") if query.get("ready") else "Verifierad kortförsäljning",
        "source_platform": str(source_platform or "eBay"),
        "currency": "SEK",
        "sold_price": 0.0,
        "shipping": "",
        "sold_url": "",
        "sold_at": "",
        "identity_verified": False,
        "sale_confirmed": False,
    }


def research_progress(exact_sold_count, target=2) -> dict:
    """Explain how much exact sold evidence is still missing; not a valuation rule."""
    try:
        count = max(0, int(exact_sold_count or 0))
    except (TypeError, ValueError):
        count = 0
    target = max(1, int(target or 1))
    remaining = max(0, target - count)
    return {
        "exact_sold_count": count,
        "target": target,
        "remaining": remaining,
        "complete": remaining == 0,
        "label": (
            f"Underlagsmål nått: {count} verifierade exakta avslut"
            if remaining == 0
            else f"{remaining} verifierat exakt avslut kvar till underlagsmålet"
        ),
        "note": "Underlagsmålet är ett researchmål och skapar inte i sig ett KÖP eller marknadsvärde.",
    }
