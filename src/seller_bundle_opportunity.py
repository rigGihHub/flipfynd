"""Same-seller basket discovery for listings where shipping may be shared.

This module never assumes combined shipping is guaranteed. It only discovers
other active listings from the same seller and quantifies a transparent
"shipping-once" scenario that the user must verify with Tradera/the seller.
"""
from __future__ import annotations

from typing import Iterable


def _seller(item: dict) -> str | None:
    for key in ("saljare", "säljare", "seller", "seller_name", "username", "seller_detail"):
        value = item.get(key)
        if value not in (None, "") and str(value).strip():
            return str(value).strip()
    return None


def _url(item: dict) -> str | None:
    value = item.get("lank") or item.get("url")
    return str(value).strip() if value else None


def _price(item: dict) -> float | None:
    for key in ("pris", "price", "current_price"):
        value = item.get(key)
        try:
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            pass
    return None


def _shipping(item: dict) -> float | None:
    value = item.get("frakt")
    try:
        if value is not None:
            number = float(value)
            return number if number >= 0 else None
    except (TypeError, ValueError):
        pass
    return None


def _identity_key(item: dict) -> str:
    return str(item.get("tradera_item_id") or _url(item) or "").strip()


def _result_map(results: Iterable[dict] | None) -> dict[str, dict]:
    out = {}
    for row in results or []:
        if not isinstance(row, dict):
            continue
        key = _identity_key(row)
        if key:
            out[key] = row
    return out


def find_same_seller_listings(current: dict, market_items: Iterable[dict] | None, *, results=None, limit: int = 12) -> dict:
    """Return other loaded listings from the same seller, best analysed first."""
    current = current or {}
    seller = _seller(current)
    current_key = _identity_key(current)
    if not seller:
        return {"status": "NO_SELLER", "seller": None, "rows": [], "count": 0}

    analysed = _result_map(results)
    rows = []
    for raw in market_items or []:
        if not isinstance(raw, dict) or _seller(raw) != seller:
            continue
        key = _identity_key(raw)
        if key and current_key and key == current_key:
            continue
        merged = dict(raw)
        if key and key in analysed:
            merged.update(analysed[key])
        price = _price(merged)
        if price is None:
            continue
        score = merged.get("fyndpotential")
        if score is None:
            score = merged.get("opportunity_score")
        if score is None:
            score = merged.get("score")
        try:
            score = float(score) if score is not None else None
        except (TypeError, ValueError):
            score = None
        rows.append({
            "title": str(merged.get("titel") or merged.get("title") or "Kortannons"),
            "price": price,
            "shipping": _shipping(merged),
            "url": _url(merged),
            "decision": merged.get("beslut") or merged.get("decision"),
            "potential": score,
            "sold_comps": int(merged.get("sold_comparable_count") or merged.get("sold_comps") or 0),
            "identity_ok": bool(merged.get("exact_identity_gate_supports_exact_comp_search") or merged.get("identity_ok")),
            "analysed": bool(key and key in analysed),
            "source_item": merged,
        })

    rows.sort(key=lambda r: (
        0 if str(r.get("decision") or "").upper() == "KÖP" else 1,
        0 if r.get("analysed") else 1,
        -(r.get("potential") if isinstance(r.get("potential"), (int, float)) else -1),
        r.get("price", 10**9),
    ))
    rows = rows[: max(1, int(limit))]
    return {"status": "FOUND" if rows else "NONE_FOUND", "seller": seller, "rows": rows, "count": len(rows)}



def classify_same_seller_addon(row: dict) -> dict:
    """Classify an extra same-seller listing without letting shared shipping rescue a weak card.

    The label is deliberately conservative. Shipping efficiency can improve the
    basket economics, but an add-on still needs its own evidence/quality signal.
    """
    row = row or {}
    analysed = bool(row.get("analysed"))
    decision = str(row.get("decision") or "").strip().upper()
    potential = row.get("potential")
    try:
        potential = float(potential) if potential is not None else None
    except (TypeError, ValueError):
        potential = None
    sold = row.get("sold_comps")
    try:
        sold = int(sold or 0)
    except (TypeError, ValueError):
        sold = 0
    identity_ok = bool(row.get("identity_ok"))

    if not analysed:
        return {
            "status": "REVIEW",
            "label": "MÖJLIGEN – analysera först",
            "reason": "Kortet är inte fullanalyserat ännu. Delad frakt är inte tillräckligt skäl för att köpa.",
        }

    if decision == "KÖP" and identity_ok and sold >= 1 and (potential is None or potential >= 55):
        return {
            "status": "ADD",
            "label": "LÄGG TILL I SAMMA PAKET",
            "reason": "Kortet står på egna meriter och samfrakt kan förbättra totalekonomin ytterligare.",
        }

    if decision == "KÖP" and (identity_ok or sold >= 1):
        return {
            "status": "REVIEW",
            "label": "MÖJLIGEN",
            "reason": "Köpsignalen finns, men identitet eller SOLD-underlag är fortfarande för tunt för automatisk add-on-rekommendation.",
        }

    if potential is not None and potential >= 60 and (identity_ok or sold >= 1):
        return {
            "status": "REVIEW",
            "label": "MÖJLIGEN",
            "reason": "Intressant kandidat, men inte tillräckligt stark för att rekommenderas enbart för att frakten kan delas.",
        }

    return {
        "status": "SKIP",
        "label": "HOPPA ÖVER",
        "reason": "Samfrakt gör inte ett svagt eller otillräckligt verifierat kort till ett fynd.",
    }

def build_shared_shipping_scenario(current: dict, selected_rows: Iterable[dict]) -> dict:
    """Transparent scenario: item prices + one shipping charge.

    The single shipping charge is the highest *known* shipping among selected
    listings/current listing. If any shipping is unknown the scenario is marked
    incomplete and is never presented as a guaranteed checkout total.
    """
    items = [current] + [r.get("source_item", r) for r in selected_rows or [] if isinstance(r, dict)]
    prices = [_price(x) for x in items]
    if any(p is None for p in prices):
        return {"status": "INCOMPLETE", "reason": "pris saknas"}
    shippings = [_shipping(x) for x in items]
    known_shipping = [s for s in shippings if s is not None]
    all_shipping_known = len(known_shipping) == len(items)
    item_total = sum(float(p) for p in prices if p is not None)
    shipping_once = max(known_shipping) if known_shipping else None
    separate_shipping = sum(known_shipping) if all_shipping_known else None
    potential_saving = (separate_shipping - shipping_once) if separate_shipping is not None and shipping_once is not None else None
    return {
        "status": "READY" if all_shipping_known else "PARTIAL",
        "item_total": round(item_total, 2),
        "shipping_once": round(shipping_once, 2) if shipping_once is not None else None,
        "scenario_total": round(item_total + shipping_once, 2) if shipping_once is not None else None,
        "separate_shipping": round(separate_shipping, 2) if separate_shipping is not None else None,
        "potential_shipping_saving": round(potential_saving, 2) if potential_saving is not None else None,
        "listing_count": len(items),
        "note": "Scenario endast. Samfrakt och slutlig frakt måste verifieras hos Tradera/säljaren.",
    }


def build_best_same_seller_basket(current: dict, rows: Iterable[dict], budget: float, *, max_addons: int = 6) -> dict:
    """Build a conservative best basket under budget, always including the anchor listing.

    Only rows classified as ADD are eligible for automatic inclusion. Unknown
    shipping is excluded from the optimiser because we must not claim a basket
    is under budget when the shipping total is not known. The objective rewards
    stronger opportunity scores and evidence, not merely the number of cards.
    """
    try:
        budget = float(budget)
    except (TypeError, ValueError):
        return {"status": "INVALID_BUDGET", "selected": [], "reason": "ogiltig budget"}
    if budget <= 0:
        return {"status": "INVALID_BUDGET", "selected": [], "reason": "ogiltig budget"}

    anchor_price = _price(current)
    anchor_shipping = _shipping(current)
    if anchor_price is None or anchor_shipping is None:
        return {"status": "INCOMPLETE_ANCHOR", "selected": [], "reason": "pris eller frakt saknas på huvudkortet"}

    base_total = anchor_price + anchor_shipping
    if base_total > budget:
        return {
            "status": "ANCHOR_OVER_BUDGET",
            "selected": [],
            "anchor_total": round(base_total, 2),
            "budget": round(budget, 2),
        }

    eligible = []
    excluded_unknown_shipping = 0
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        addon = classify_same_seller_addon(row)
        if addon.get("status") != "ADD":
            continue
        price = row.get("price")
        shipping = row.get("shipping")
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue
        if shipping is None:
            excluded_unknown_shipping += 1
            continue
        try:
            shipping = float(shipping)
        except (TypeError, ValueError):
            excluded_unknown_shipping += 1
            continue

        potential = row.get("potential")
        try:
            potential = float(potential) if potential is not None else 55.0
        except (TypeError, ValueError):
            potential = 55.0
        sold = row.get("sold_comps")
        try:
            sold = int(sold or 0)
        except (TypeError, ValueError):
            sold = 0
        # Evidence-aware basket utility. Price is handled by the budget itself;
        # score favours stronger cards rather than maximising card count.
        utility = potential + min(sold, 5) * 4 + (8 if row.get("identity_ok") else 0)
        eligible.append((row, price, shipping, utility))

    if not eligible:
        return {
            "status": "NO_ELIGIBLE_ADDONS",
            "selected": [],
            "budget": round(budget, 2),
            "anchor_total": round(base_total, 2),
            "excluded_unknown_shipping": excluded_unknown_shipping,
        }

    best = {"utility": -1.0, "selected": [], "scenario_total": base_total}
    n = len(eligible)
    # Same-seller popover is capped to a small list, so exhaustive combinations
    # remain tiny and make the optimisation transparent/deterministic.
    from itertools import combinations
    for r in range(1, min(max_addons, n) + 1):
        for combo in combinations(eligible, r):
            selected_rows = [x[0] for x in combo]
            scenario = build_shared_shipping_scenario(current, selected_rows)
            total = scenario.get("scenario_total")
            if total is None or total > budget:
                continue
            utility = sum(x[3] for x in combo)
            # Tie-break: higher utility, then lower spend, then more cards.
            key = (utility, -float(total), len(combo))
            best_key = (best["utility"], -float(best["scenario_total"]), len(best["selected"]))
            if key > best_key:
                best = {
                    "utility": utility,
                    "selected": selected_rows,
                    "scenario_total": float(total),
                    "scenario": scenario,
                }

    if not best["selected"]:
        return {
            "status": "NO_FIT",
            "selected": [],
            "budget": round(budget, 2),
            "anchor_total": round(base_total, 2),
            "eligible_count": len(eligible),
            "excluded_unknown_shipping": excluded_unknown_shipping,
        }

    return {
        "status": "FOUND",
        "selected": best["selected"],
        "selected_count": len(best["selected"]),
        "utility": round(best["utility"], 2),
        "budget": round(budget, 2),
        "scenario_total": round(best["scenario_total"], 2),
        "scenario": best.get("scenario", {}),
        "remaining_budget": round(budget - best["scenario_total"], 2),
        "eligible_count": len(eligible),
        "excluded_unknown_shipping": excluded_unknown_shipping,
        "note": "Automatisk korg använder bara redan starka add-on-kandidater med känd frakt. Samfrakt måste fortfarande verifieras hos säljaren.",
    }
