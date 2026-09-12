"""Research shortlist for markets where verified comps are still missing.

This is deliberately NOT a buy list. It helps the user see which listings are
worth verifying next when the strict economic-edge gate has no eligible rows.
"""
from __future__ import annotations


def _n(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _txt(v):
    return " ".join(str(v or "").strip().split())


def _player_key(item):
    fields = item.get("exact_identity_gate_identity_fields") or {}
    if isinstance(fields, dict) and fields.get("player_name"):
        return _txt(fields.get("player_name")).casefold()
    for key in ("player_name", "matched_player_name", "player_match_name", "spelare"):
        if item.get(key):
            return _txt(item.get(key)).casefold()
    return ""


def evidence_coverage(items):
    items = list(items or [])
    total = len(items)
    if not total:
        return {"total": 0, "with_sold": 0, "with_2_sold": 0, "identity_ready": 0, "market_value_ready": 0, "max_price_ready": 0}
    out = {"total": total, "with_sold": 0, "with_2_sold": 0, "identity_ready": 0, "market_value_ready": 0, "max_price_ready": 0}
    for item in items:
        sold = int(_n(item.get("sold_comparable_count"), 0))
        out["with_sold"] += sold >= 1
        out["with_2_sold"] += sold >= 2
        out["identity_ready"] += bool(item.get("exact_identity_gate_supports_exact_comp_search") or item.get("exact_identity_gate_status") in {"READY", "EXACT", "STRONG"})
        out["market_value_ready"] += bool(item.get("valuation_display_safe") is True and any(item.get(k) is not None for k in ("market_value_estimate", "expected_resale", "estimated_market_value", "marknadsvarde")))
        out["max_price_ready"] += _n(item.get("dynamic_max_total_price") or item.get("max_total_price"), 0) > 0
    return out


def _score(item):
    potential = max(0.0, min(100.0, _n(item.get("deal_score"))))
    score = potential * 0.45
    if item.get("exact_identity_gate_supports_exact_comp_search"):
        score += 22
    elif item.get("observed_identity_score") or item.get("identity_observed_score"):
        score += min(12, _n(item.get("observed_identity_score") or item.get("identity_observed_score")) * 0.12)
    sold = int(_n(item.get("sold_comparable_count"), 0))
    score += min(18, sold * 7)
    if item.get("is_market_edge_candidate") or item.get("is_information_edge_candidate"):
        score += 10
    if item.get("mispriced_rookie_candidate") or item.get("misclassified_card_candidate") or item.get("is_hidden_find_candidate"):
        score += 8
    # Collector/player prestige is only a weak tie-breaker, never the engine.
    score += min(5, _n(item.get("collector_worth_score")) * 0.05)
    return score


def build_research_shortlist(items, limit=5):
    rows = []
    for item in items or []:
        title = _txt(item.get("titel") or item.get("title"))
        if not title:
            continue
        sold = int(_n(item.get("sold_comparable_count"), 0))
        identity_ready = bool(item.get("exact_identity_gate_supports_exact_comp_search") or item.get("exact_identity_gate_status") in {"READY", "EXACT", "STRONG"})
        reasons = []
        if identity_ready:
            reasons.append("identiteten är tillräckligt stark för exact-comp-sökning")
        else:
            reasons.append("identiteten behöver verifieras")
        if sold == 0:
            reasons.append("saknar verifierade SOLD-comps")
        elif sold == 1:
            reasons.append("har bara 1 verifierad SOLD-comp")
        if item.get("is_market_edge_candidate") or item.get("is_information_edge_candidate"):
            reasons.append("har en observerad marknads-/informationssignal")
        if item.get("is_hidden_find_candidate") or item.get("misclassified_card_candidate") or item.get("mispriced_rookie_candidate"):
            reasons.append("har en discovery-signal värd att kontrollera")
        rows.append({
            "title": title,
            "url": item.get("lank") or item.get("url"),
            "player_key": _player_key(item),
            "score": _score(item),
            "potential": max(0.0, min(100.0, _n(item.get("deal_score")))),
            "sold_comps": sold,
            "identity_ready": identity_ready,
            "reasons": reasons[:3],
            "source_item": item,
        })
    rows.sort(key=lambda r: (r["score"], r["identity_ready"], r["sold_comps"], r["potential"]), reverse=True)
    selected, used = [], set()
    for row in rows:
        pk = row.get("player_key")
        if pk and pk in used:
            continue
        selected.append(row)
        if pk:
            used.add(pk)
        if len(selected) >= limit:
            break
    for row in rows:
        if len(selected) >= limit:
            break
        if row not in selected:
            selected.append(row)
    return selected
