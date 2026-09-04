import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

SCHEMA_VERSION = 3


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _days_between(start: Optional[str], end: Optional[str]) -> Optional[int]:
    if not start or not end:
        return None
    try:
        a = datetime.fromisoformat(start.replace("Z", "+00:00"))
        b = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0, (b.date() - a.date()).days)


def load_journal(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = payload.get("entries", []) if isinstance(payload, dict) else payload
    return [row for row in rows if isinstance(row, dict)]


def save_journal(entries: Iterable[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": SCHEMA_VERSION, "updated_at": _utc_now(), "entries": list(entries)}
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def hashlib_key(primary: str, salt: str = "") -> str:
    import hashlib
    return hashlib.sha1(f"{primary}|{salt}".encode("utf-8")).hexdigest()[:16]


def build_entry_from_listing(item: dict, purchase_price: Optional[float] = None, purchase_date: Optional[str] = None) -> dict:
    now = _utc_now()
    purchase_price = _to_float(purchase_price)
    return {
        "id": hashlib_key(item.get("lank") or item.get("titel") or now, now),
        "created_at": now,
        "updated_at": now,
        "status": "köpt" if purchase_price is not None else "bevakning",
        "listing_url": item.get("lank") or "",
        "title": item.get("titel") or "Okänd annons",
        "sport": item.get("sport") or item.get("category") or "",
        "player_name": item.get("player_name") or "",
        "recommended_decision": item.get("beslut") or item.get("decision") or "",
        "deal_score_at_capture": _to_float(item.get("deal_score")),
        "deal_confidence_at_capture": _to_float(item.get("deal_confidence_score")),
        "valuation_confidence_at_capture": _to_float(item.get("valuation_confidence_score")),
        "risk_score_at_capture": _to_float(item.get("risk_score")),
        "sellability_at_capture": _to_float(item.get("liquidity_score")) or _to_float(item.get("liquidity")),
        "exact_comp_available_at_capture": bool((item.get("sold_comparable_count") or 0) > 0),
        "decision_confidence_downgraded_at_capture": bool(item.get("decision_confidence_audit_downgraded")),
        "decision_confidence_blockers_at_capture": list(item.get("decision_confidence_audit_blockers") or []),
        "decision_conflict_downgraded_at_capture": bool(item.get("decision_conflict_audit_downgraded")),
        "decision_conflicts_at_capture": list(item.get("decision_conflict_audit_conflicts") or []),
        "expected_resale_at_capture": _to_float(item.get("expected_resale_price")) or _to_float(item.get("realistic_value")),
        "expected_net_profit_at_capture": _to_float(item.get("net_profit")),
        "max_total_price_at_capture": _to_float(item.get("max_total_price")),
        "flip_velocity_days_at_capture": _to_float(item.get("flip_velocity_expected_days")),
        "information_edge_score_at_capture": _to_float(item.get("information_edge_score")),
        "information_edge_candidate_at_capture": bool(item.get("is_information_edge_candidate")),
        "hidden_find_score_at_capture": _to_float(item.get("hidden_find_score")),
        "hidden_find_candidate_at_capture": bool(item.get("is_hidden_find_candidate")),
        "market_edge_score_at_capture": _to_float(item.get("market_edge_score")),
        "market_edge_candidate_at_capture": bool(item.get("is_market_edge_candidate")),
        "mispriced_rookie_candidate_at_capture": bool(item.get("mispriced_rookie_candidate")),
        "misclassified_card_candidate_at_capture": bool(item.get("misclassified_card_candidate")),
        "purchase_date": purchase_date or (datetime.now().date().isoformat() if purchase_price is not None else None),
        "purchase_price": purchase_price,
        "sale_date": None,
        "sale_price": None,
        "selling_fee": None,
        "packaging_cost": None,
        "other_cost": None,
        "actual_net_profit": None,
        "days_to_sell": None,
        "notes": "",
        "outcome_review_reasons": [],
        "outcome_review_note": "",
        "outcome_reviewed_at": None,
    }


def update_entry(entries: list[dict], entry_id: str, **changes: Any) -> list[dict]:
    updated = []
    found = False
    for row in entries:
        if row.get("id") != entry_id:
            updated.append(row)
            continue
        found = True
        new_row = dict(row)
        for key, value in changes.items():
            if key in {"purchase_price", "sale_price", "selling_fee", "packaging_cost", "other_cost"}:
                value = _to_float(value)
            new_row[key] = value
        new_row["updated_at"] = _utc_now()
        if new_row.get("sale_price") is not None:
            purchase = _to_float(new_row.get("purchase_price")) or 0.0
            fee = _to_float(new_row.get("selling_fee")) or 0.0
            packaging = _to_float(new_row.get("packaging_cost")) or 0.0
            other = _to_float(new_row.get("other_cost")) or 0.0
            new_row["actual_net_profit"] = float(new_row["sale_price"]) - purchase - fee - packaging - other
            new_row["actual_roi_pct"] = (new_row["actual_net_profit"] / purchase * 100) if purchase > 0 else None
            new_row["days_to_sell"] = _days_between(new_row.get("purchase_date"), new_row.get("sale_date"))
            new_row["status"] = "sålt"
        elif new_row.get("purchase_price") is not None:
            new_row["status"] = "köpt"
        updated.append(new_row)
    if not found:
        raise KeyError(entry_id)
    return updated


def journal_metrics(entries: Iterable[dict]) -> dict:
    rows = list(entries)
    sold = [r for r in rows if r.get("status") == "sålt" and _to_float(r.get("actual_net_profit")) is not None]
    bought_open = [r for r in rows if r.get("status") == "köpt"]
    profits = [_to_float(r.get("actual_net_profit")) for r in sold]
    profits = [p for p in profits if p is not None]
    days = [r.get("days_to_sell") for r in sold if isinstance(r.get("days_to_sell"), int)]
    prediction_errors = []
    for r in sold:
        expected = _to_float(r.get("expected_net_profit_at_capture"))
        actual = _to_float(r.get("actual_net_profit"))
        if expected is not None and actual is not None:
            prediction_errors.append(actual - expected)
    return {
        "entry_count": len(rows),
        "sold_count": len(sold),
        "open_count": len(bought_open),
        "actual_net_profit_total": round(sum(profits), 2),
        "win_rate": round(sum(1 for p in profits if p > 0) / len(profits) * 100, 1) if profits else None,
        "median_days_to_sell": sorted(days)[len(days)//2] if days else None,
        "mean_profit_error": round(sum(prediction_errors) / len(prediction_errors), 2) if prediction_errors else None,
    }
