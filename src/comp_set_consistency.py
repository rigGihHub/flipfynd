"""Collapse repeated exact-comp records into independent market observations.

This module is deliberately conservative. It only collapses observations when
there is strong evidence they represent the same realised sale. Price/date alone
never qualifies as a duplicate.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Iterable
from urllib.parse import urlparse


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _price(row: dict) -> str:
    value = row.get("price") if row.get("price") not in (None, "") else row.get("sold_price")
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return ""


def _date(row: dict) -> str:
    value = row.get("sold_at") or row.get("sold_date") or row.get("date") or ""
    return str(value).strip()[:10]


def _explicit_id(row: dict) -> str:
    for key in ("external_sale_id", "sale_id", "listing_id", "item_id", "sold_comp_id"):
        value = str(row.get(key) or "").strip()
        if value:
            return f"id:{key}:{value.casefold()}"
    return ""


def _url_key(row: dict) -> str:
    raw = str(row.get("lank") or row.get("url") or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
        host = parsed.netloc.casefold().removeprefix("www.")
        path = re.sub(r"/+", "/", parsed.path.rstrip("/")).casefold()
        if host and path:
            return f"url:{host}{path}"
    except Exception:
        pass
    return f"url:{raw.casefold()}"


def _identity_key(row: dict) -> str:
    fields = [
        row.get("player_name") or row.get("player"),
        row.get("season") or row.get("year"),
        row.get("set_name") or row.get("set") or row.get("product"),
        row.get("card_number") or row.get("checklist_number"),
        row.get("parallel") or row.get("variant"),
        row.get("serial_denominator") or row.get("serial_number"),
        row.get("grading_company"),
        row.get("grade"),
        row.get("is_auto"),
        row.get("is_patch"),
    ]
    values = [_norm(v) for v in fields]
    # Require the core identity to exist. Otherwise fallback dedupe is unsafe.
    if not all(values[i] for i in (0, 1, 2, 3)):
        return ""
    return "|".join(values)


def _fallback_signature(row: dict) -> str:
    """High-confidence mirrored-sale signature.

    Requires exact identity + date + price + seller + title. This intentionally
    does not merge same-price/same-date rows when seller or title is missing.
    """
    identity = _identity_key(row)
    sold_date = _date(row)
    price = _price(row)
    seller = _norm(row.get("saljare") or row.get("seller") or row.get("seller_name"))
    title = _norm(row.get("titel") or row.get("title"))
    if not all((identity, sold_date, price, seller, title)):
        return ""
    return f"mirror:{identity}|{sold_date}|{price}|{seller}|{title}"


def _keys(row: dict) -> list[str]:
    keys = []
    for key in (_explicit_id(row), _url_key(row), _fallback_signature(row)):
        if key:
            keys.append(key)
    return keys


def collapse_independent_observations(rows: Iterable[dict] | None) -> dict[str, Any]:
    raw = [dict(r) for r in (rows or []) if isinstance(r, dict)]
    if not raw:
        return {
            "rows": [], "raw_count": 0, "independent_count": 0,
            "duplicate_count": 0, "duplicate_clusters": [],
            "note": "Inga Exact-comps att kontrollera för upprepade observationer.",
        }

    # Union-find lets URL/ID/fallback keys connect records without relying on
    # input order or source order.
    parent = list(range(len(raw)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    seen: dict[str, int] = {}
    matched_keys: dict[tuple[int, int], list[str]] = defaultdict(list)
    for idx, row in enumerate(raw):
        for key in _keys(row):
            if key in seen:
                other = seen[key]
                union(idx, other)
                pair = tuple(sorted((idx, other)))
                matched_keys[pair].append(key.split(":", 1)[0])
            else:
                seen[key] = idx

    groups: dict[int, list[int]] = defaultdict(list)
    for idx in range(len(raw)):
        groups[find(idx)].append(idx)

    independent = []
    clusters = []
    for indices in sorted(groups.values(), key=lambda g: min(g)):
        independent.append(raw[min(indices)])
        if len(indices) > 1:
            reasons = set()
            for (a, b), kinds in matched_keys.items():
                if a in indices and b in indices:
                    reasons.update(kinds)
            clusters.append({
                "size": len(indices),
                "indices": [i + 1 for i in indices],
                "reason_types": sorted(reasons),
                "representative_title": raw[min(indices)].get("titel") or raw[min(indices)].get("title"),
            })

    return {
        "rows": independent,
        "raw_count": len(raw),
        "independent_count": len(independent),
        "duplicate_count": len(raw) - len(independent),
        "duplicate_clusters": clusters,
        "note": "Samma försäljning kollapsas via explicit ID/URL eller en högkonfidenssignatur. Pris + datum ensamt räcker aldrig för deduplicering.",
    }
