"""Information Edge Hunter.

Prioritises listings where FlipFynd may know *what to verify* better than the
seller/title communicates. This is deliberately a review signal only: it must
never create a valuation, profit, max bid or BUY decision.
"""
from __future__ import annotations

IMPORTANT_FIELDS = {
    "parallel": "parallel/variant",
    "serial_numbered": "numrering",
    "card_number": "kortnummer",
    "autograph": "autograf",
    "patch": "patch/relic",
    "rookie": "rookiestatus",
    "grade": "gradering",
    "set_name": "set/produkt",
    "season": "säsong/år",
}


def build_information_edge_hunter(*, item: dict, features: dict, listing_quality: dict,
                                  hidden_find: dict, market_edge: dict, visual_edge: dict,
                                  identity_gate: dict | None = None) -> dict:
    """Return a conservative information-asymmetry review signal."""
    enriched = set(features.get("identity_enriched_fields") or [])
    hidden_fields = [IMPORTANT_FIELDS[x] for x in IMPORTANT_FIELDS if x in enriched]
    score = 0.0
    reasons: list[str] = []
    verify: list[str] = []

    lq = float((listing_quality or {}).get("score", 0) or 0)
    hidden_score = float((hidden_find or {}).get("score", 0) or 0)
    edge_score = float((market_edge or {}).get("score", 0) or 0)
    visual_score = float((visual_edge or {}).get("score", 0) or 0)

    if hidden_fields:
        score += min(34, 12 + 5 * len(hidden_fields))
        reasons.append("annonsinformationen innehåller viktigare kortdetaljer än rubriken")
        verify.extend(hidden_fields[:4])
    if lq < 55:
        score += 20
        reasons.append("svag annonsbeskrivning kan skapa informationsövertag")
    elif lq < 70:
        score += 10
    if hidden_score >= 55:
        score += 18
        reasons.append("annonsen är svårare än normalt att hitta via exakt sökning")
    if edge_score >= 50:
        score += 16
        reasons.append("Edge Engine ser ett separat informationsgap")
    if visual_score >= 55:
        score += 12
        reasons.append("bildkontroll kan avslöja detaljer som texten inte säkert fastställer")
        verify.append("fram-/baksida på kortet")

    title = str(item.get("titel") or item.get("title") or "").strip()
    if len(title) < 28:
        score += 8
        reasons.append("ovanligt kort rubrik")

    # Lots can hide cards, but are also materially harder to verify safely.
    if features.get("is_lot"):
        score += 8
        reasons.append("lot/paket kan gömma ett enskilt intressant kort")
        verify.append("att annonsen verkligen avser rätt enskilt kort")

    gate_status = str((identity_gate or {}).get("status") or "").upper()
    if gate_status in {"LÅST", "LOCKED"}:
        score = min(score, 64)
        reasons.append("identiteten är låst – verifiering krävs innan någon affärsbedömning")

    score = round(max(0, min(100, score)), 1)
    candidate = score >= 55
    if score >= 75:
        label = "Starkt informationsövertag"
    elif candidate:
        label = "Potentiellt informationsövertag"
    elif score >= 35:
        label = "Värt manuell kontroll"
    else:
        label = "Ingen tydlig informationsedge"

    # Deduplicate while preserving order.
    verify = list(dict.fromkeys(verify))
    if candidate and not verify:
        verify = ["exakt kortidentitet mot bilder och annonsdetaljer"]

    return {
        "score": score,
        "label": label,
        "is_candidate": candidate,
        "reasons": reasons[:5],
        "verify_first": verify[:5],
        "review_only": True,
        "can_create_value": False,
        "can_create_buy_decision": False,
        "note": "Informationsedge prioriterar manuell kontroll. Den skapar aldrig marknadsvärde, vinst eller köpbeslut.",
    }
