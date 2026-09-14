"""Rank the best current FlipFynd opportunities from one Tradera seller."""
from __future__ import annotations

from typing import Callable, Iterable

from src.seller_card_domain import seller_item_domain_check
from src.seller_live_quick_analysis import quick_analyze_seller_inventory
from src.seller_live_full_analysis import full_analyze_live_seller_item


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _identity_key(item: dict) -> str:
    for key in ("tradera_item_id", "id", "item_id", "lank", "url", "link"):
        value = item.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return str(item.get("titel") or item.get("title") or "").strip().casefold()


def _rank_key(row: dict):
    decision = str(row.get("decision") or "").upper()
    is_buy = decision.startswith("KÖP")
    sold = int(_num(row.get("sold_comps")))
    identity_ok = bool(row.get("identity_ok"))
    edge = _num(row.get("market_edge"))
    valuation = _num(row.get("valuation_confidence"))
    quick = _num(row.get("quick_score"))
    price = _num(row.get("price"), 10**12)
    return (0 if is_buy else 1, 0 if identity_ok and sold >= 2 else 1, -sold, -edge, -valuation, -quick, price)


def _quick_rank_key(row: dict):
    decision = str(row.get("decision") or "").upper()
    sold = int(_num(row.get("sold_comps")))
    identity_ok = bool(row.get("identity_ok"))
    return (
        0 if decision.startswith("KÖP") else 1,
        0 if identity_ok and sold > 0 else 1,
        -sold,
        -_num(row.get("market_edge")),
        -_num(row.get("valuation_confidence")),
        -_num(row.get("quick_score")),
        _num(row.get("price"), 10**12),
    )


def _display_worthy(row: dict) -> bool:
    decision = str(row.get("decision") or "").upper().strip()
    if decision.startswith("KÖP"):
        return True
    if decision.startswith("UNDERSÖK"):
        return True
    # Do not pad Seller Top 5 with SKIP/insufficient-underlag rows.
    return False


def _quick_scan_inventory(alias: str, inventory: list[dict], *, analyze_fn: Callable, sport: str, quick_limit: int) -> dict:
    anchor = {"saljare": alias, "tradera_item_id": "__seller_top5_anchor__"}
    batch_size = max(20, min(int(quick_limit or 60), 100))
    unique: dict[str, dict] = {}
    for row in inventory:
        key = _identity_key(row)
        if key:
            unique[key] = row
    unique_inventory = list(unique.values())

    all_rows: dict[str, dict] = {}
    failed = 0
    batches = 0
    for start in range(0, len(unique_inventory), batch_size):
        batch = unique_inventory[start:start + batch_size]
        if not batch:
            continue
        batches += 1
        quick = quick_analyze_seller_inventory(
            anchor, batch, analyze_fn=analyze_fn, sport=sport,
            strategy_mode="quick_flip", limit=len(batch), shortlist=min(5, len(batch)),
        )
        failed += int(quick.get("failed_count") or 0)
        for row in quick.get("rows") or []:
            source = row.get("source_item") or {}
            key = _identity_key(source) or _identity_key(row)
            if not key:
                continue
            previous = all_rows.get(key)
            if previous is None or _quick_rank_key(row) < _quick_rank_key(previous):
                all_rows[key] = row

    rows = list(all_rows.values())
    rows.sort(key=_quick_rank_key)
    return {
        "rows": rows,
        "analysed_count": len(rows),
        "failed_count": failed,
        "batch_count": batches,
        "inventory_unique_count": len(unique_inventory),
        "coverage_complete": len(rows) + failed >= len(unique_inventory),
    }


def build_seller_top5(seller_alias: str, items: Iterable[dict] | None, *, analyze_fn: Callable,
                      sport: str = "hockey", quick_limit: int = 60, full_limit: int = 10) -> dict:
    alias = str(seller_alias or "").strip()
    raw_inventory = [dict(x) for x in (items or []) if isinstance(x, dict)]
    if not alias:
        return {"status": "NO_SELLER", "rows": [], "seller": None, "inventory_count": len(raw_inventory)}
    if not raw_inventory:
        return {"status": "NO_ITEMS", "rows": [], "seller": alias, "inventory_count": 0}

    rejected = []
    inventory = []
    for item in raw_inventory:
        check = seller_item_domain_check(item, sport=sport)
        if check.get("allowed"):
            inventory.append(item)
        else:
            rejected.append({"title": check.get("title"), "reason": check.get("reason")})

    if not inventory:
        return {
            "status": "NO_CARD_ITEMS", "rows": [], "seller": alias,
            "inventory_count": len(raw_inventory), "card_inventory_count": 0,
            "domain_rejected_count": len(rejected),
        }

    quick = _quick_scan_inventory(alias, inventory, analyze_fn=analyze_fn, sport=sport, quick_limit=quick_limit)
    candidate_limit = max(5, min(int(full_limit), 20))
    candidates = list(quick.get("rows") or [])[:candidate_limit]
    full_rows = []
    failed = 0
    for qrow in candidates:
        source_item = qrow.get("source_item") or {}
        try:
            full = full_analyze_live_seller_item(
                source_item, analyze_fn=analyze_fn, all_items=inventory,
                sport=sport, strategy_mode="quick_flip",
            )
        except Exception:
            failed += 1
            continue
        row = dict(full)
        row["quick_score"] = qrow.get("quick_score")
        row["seller"] = alias
        if _display_worthy(row):
            full_rows.append(row)

    common_meta = {
        "seller": alias,
        "inventory_count": len(raw_inventory),
        "card_inventory_count": len(inventory),
        "domain_rejected_count": len(rejected),
        "inventory_unique_count": int(quick.get("inventory_unique_count") or 0),
        "quick_analysed": int(quick.get("analysed_count") or 0),
        "quick_failed": int(quick.get("failed_count") or 0),
        "quick_batches": int(quick.get("batch_count") or 0),
        "coverage_complete": bool(quick.get("coverage_complete")),
    }

    if not full_rows:
        # Do not manufacture five weak rows. Only quick rows already labelled
        # UNDERSÖK may survive as explicit research candidates.
        fallback = []
        for qrow in quick.get("rows") or []:
            if not str(qrow.get("decision") or "").upper().startswith("UNDERSÖK"):
                continue
            fallback.append({
                "title": qrow.get("title"), "price": qrow.get("price"), "url": qrow.get("url"),
                "decision": "UNDERSÖK", "label": "VÄRT ATT UNDERSÖKA",
                "reason": qrow.get("reason") or "Behöver verifieras innan köp.",
                "identity_ok": qrow.get("identity_ok"), "sold_comps": qrow.get("sold_comps", 0),
                "valuation_confidence": qrow.get("valuation_confidence", 0),
                "market_edge": qrow.get("market_edge", 0), "quick_score": qrow.get("quick_score", 0),
                "seller": alias, "source_item": qrow.get("source_item") or {},
            })
            if len(fallback) >= 5:
                break
        return {
            "status": "QUICK_ONLY" if fallback else "NO_STRONG_CANDIDATES",
            "rows": fallback, "full_analysed": 0, "failed_full": failed, **common_meta,
        }

    full_rows.sort(key=_rank_key)
    return {
        "status": "READY", "rows": full_rows[:5], "full_analysed": len(full_rows),
        "failed_full": failed, **common_meta,
    }
