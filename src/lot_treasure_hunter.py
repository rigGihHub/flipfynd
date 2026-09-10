"""Lot Treasure Hunter.

Finds lots/bundles that deserve manual card-by-card inspection using only evidence
already present in FlipFynd. It never assigns value to an unseen card, divides a lot
price into invented per-card values, or turns a lot into BUY.
"""
from __future__ import annotations


def _n(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def build_lot_treasure_signal(item: dict | None) -> dict:
    item = item or {}
    is_lot = bool(item.get("is_lot") or item.get("lot_count"))
    if not is_lot:
        return {
            "is_lot": False,
            "candidate": False,
            "label": "Inte en identifierad lot/paket-annons",
            "reasons": [],
            "verify_first": [],
            "review_only": True,
            "can_create_buy_decision": False,
            "can_create_market_value": False,
            "can_allocate_per_card_value": False,
        }

    reasons, verify, evidence_types = [], [], []
    lot_count = item.get("lot_count")
    lot_confidence = str(item.get("lot_confidence") or "none")

    if lot_count:
        reasons.append(f"Annonsen verkar omfatta {int(_n(lot_count))} kort.")
        evidence_types.append("explicit-lot-count")
    elif lot_confidence and lot_confidence != "none":
        reasons.append(f"Lot/paket är identifierat med befintlig säkerhetsnivå: {lot_confidence}.")
        evidence_types.append("lot-detection")

    if item.get("is_information_edge_candidate"):
        evidence_types.append("information-gap")
        reasons.extend(list(item.get("information_edge_reasons") or [])[:3])
        verify.extend(list(item.get("information_edge_verify_first") or [])[:4])

    if item.get("is_hidden_find_candidate"):
        evidence_types.append("underexposed-listing")
        reasons.extend(list(item.get("hidden_find_reasons") or [])[:3])

    if _n(item.get("visual_edge_score")) >= 55 or item.get("visual_verification_required"):
        evidence_types.append("visual-review")
        reasons.append("Befintlig bildsignal säger att bilderna bör granskas manuellt.")
        verify.append("samtliga synliga kort på fram-/baksida")

    tags = list(item.get("valuable_card_tags") or [])
    # These tags are only useful if already established by existing card evidence;
    # they never prove that a particular valuable card is actually contained in the lot.
    if tags:
        evidence_types.append("collector-structure-signal")
        reasons.append("Befintlig analys innehåller samlarstruktur att kontrollera: " + ", ".join(map(str, tags[:4])) + ".")
        verify.append("att signalen verkligen gäller ett specifikt kort i lotten")

    if item.get("misclassified_card_candidate"):
        evidence_types.append("possible-misclassification")
        reasons.extend(list(item.get("misclassified_card_reasons") or [])[:2])

    if item.get("mispriced_rookie_candidate") or item.get("rookie_importance_matched"):
        evidence_types.append("rookie-review")
        reasons.append("Befintlig rookie-signal gör lotten värd kort-för-kort-kontroll.")
        verify.append("vilket specifikt kort rookie-signalen avser")

    # A lot alone is not a treasure candidate. It needs at least one independent
    # evidence type beyond lot detection/count.
    independent = [
        x for x in evidence_types
        if x not in {"explicit-lot-count", "lot-detection"}
    ]
    candidate = bool(independent)

    if candidate and len(set(independent)) >= 2:
        label = "Lot med flera skäl för manuell skattjakt"
    elif candidate:
        label = "Lot värd manuell kort-för-kort-kontroll"
    else:
        label = "Lot identifierad – ingen extra skattjaktssignal"

    verify.extend([
        "vilka kort som faktiskt ingår",
        "exakt identitet för varje intressant kort",
        "sold comps först efter säker kortidentitet",
    ])

    return {
        "is_lot": True,
        "candidate": candidate,
        "label": label,
        "lot_count": int(_n(lot_count)) if lot_count else None,
        "lot_confidence": lot_confidence,
        "evidence_types": list(dict.fromkeys(evidence_types)),
        "reasons": list(dict.fromkeys(str(x) for x in reasons if x))[:8],
        "verify_first": list(dict.fromkeys(str(x) for x in verify if x))[:8],
        "review_only": True,
        "can_create_buy_decision": False,
        "can_create_market_value": False,
        "can_allocate_per_card_value": False,
        "note": (
            "Lot Treasure Hunter prioriterar manuell kontroll av paket. Den antar aldrig "
            "att ett visst kort ingår och skapar aldrig styckvärden eller KÖP."
        ),
    }


def build_lot_treasure_queue(items, limit=8):
    rows=[]
    for item in items or []:
        signal=build_lot_treasure_signal(item)
        if not signal.get("candidate"):
            continue
        rows.append({
            "title": item.get("titel") or item.get("title") or "Okänd lot",
            "url": item.get("url") or item.get("lank"),
            "decision": item.get("beslut") or item.get("decision"),
            "signal": signal,
            "_priority": (
                len(signal.get("evidence_types") or []),
                _n(item.get("visual_edge_score")),
                _n(item.get("information_edge_score")),
                _n(item.get("rank_score")),
            ),
        })
    rows.sort(key=lambda r:r["_priority"], reverse=True)
    for row in rows:
        row.pop("_priority", None)
    return {
        "rows": rows[:max(0, int(limit))],
        "creates_new_decision": False,
        "creates_new_value": False,
    }
