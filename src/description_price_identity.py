"""Recover missing research fields only from the exact primary listing.

Description recovery never creates SOLD evidence or a purchase decision.
"""
from __future__ import annotations

import re
import time
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlsplit

from src.card_parser import parse_card_features, extract_season, clean_card_title
from src.research_title_identity import build_research_title_identity

_DETAIL_CACHE = globals().get("_DETAIL_CACHE", {})
_DETAIL_LOCK = globals().get("_DETAIL_LOCK", Lock())


def price_program(title):
    # Named inserts must remain distinct when their canonical set is the same.
    patterns = (
        (r"young\s*guns", "Young Guns"),
        (r"honou?r\s+roll", "Honor Roll"),
        (r"cast\s+for\s+greatness", "Cast For Greatness"),
        (r"speed\s+of\s+the\s+game", "Speed Of The Game"),
        (r"future\s+watch", "Future Watch"),
        (r"future\s+impact", "Future Impact"),
        (r"world\s+cup", "World Cup"),
        (r"team\s+pinnacle", "Team Pinnacle"),
        (r"marquee\s+rookie", "Marquee Rookie"),
        (r"star\s*quest", "Starquest"),
        (r"reflections", "Reflections"),
        (r"radiance", "Radiance"),
        (r"synergy", "Synergy"),
    )
    return "|".join(name for pattern, name in patterns if re.search(pattern, title or "", re.I))


def recover_description_identity(item):
    if not item.get("purchase_detail_verified") or item.get("listing_inactive"):
        return {}
    url = str(item.get("lank") or item.get("url") or "")
    parts = urlsplit(url)
    match = re.match(r"/item/\d+/(\d+)(?:/|$)", parts.path)
    if (parts.hostname not in {"tradera.com", "www.tradera.com"} or not match
            or item.get("purchase_detail_url") != url
            or str(item.get("purchase_detail_item_id")) != match[1]):
        return {}
    title = clean_card_title(str(item.get("titel") or item.get("title") or ""))
    parsed = parse_card_features(title)
    if not parsed.get("player_name") or not parsed.get("set_name") or parsed.get("is_lot"):
        return {}
    description = str(item.get("full_description") or "")
    # Do not extract jersey numbers, print runs, statistics or other auctions.
    token = r"([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)"
    patterns = (
        rf"#\s*{token}\b(?!\s*/\s*\d)",
        rf"\bkort(?:et)?\s+(?:är\s+)?(?:märkt|nummer|nr\.?|har\s+nummer)\s*:?\s*{token}\b",
        rf"\bkortnummer\s*:?\s*{token}\b",
    )
    numbers = {m.group(1).upper() for pattern in patterns for m in re.finditer(pattern, description, re.I)
               if re.search(r"\d", m.group(1)) and not re.match(r"(?:19|20)\d{2}-\d{2}$", m.group(1))}
    if len(numbers) > 1 or (parsed.get("card_number") and numbers and str(parsed["card_number"]).upper() not in numbers):
        return {}
    fields = {}
    if not parsed.get("card_number") and len(numbers) == 1:
        fields["card_number"] = next(iter(numbers))
    # The back-of-card biography often lists many historical seasons. Only the
    # opening product description can supply a missing issue season.
    opening = re.split(r"\bbaksidan\b|\bstatistik\b|\bsamfrakt\b|\bskickas\b", description, maxsplit=1, flags=re.I)[0][:500]
    from src.card_listing_integrity import assess_listing_integrity
    opening_features = parse_card_features(opening)
    if (not assess_listing_integrity(opening)["eligible_physical_single_card"]
            or (opening_features.get("set_name") and opening_features["set_name"] != parsed["set_name"])):
        return {}
    seasons = {extract_season(m.group(0)) for m in re.finditer(r"(?<!\d)(?:19|20)\d{2}\s*[-/]\s*(?:(?:19|20)?\d{2})\b", opening)}
    seasons.discard(None)
    if parsed.get("season") and seasons and parsed["season"] not in seasons:
        return {}
    if not parsed.get("season") and len(seasons) == 1:
        fields["season"] = next(iter(seasons))
    return fields


def enrich_description_routes(rows, *, limit=80, verifier=None):
    """Bound HTTP detail work to cheap identifiable cards missing a number."""
    from src.tradera_purchase_cost import verify_purchase_cost
    from src.search_progress import begin_phase, report_phase
    verifier = verifier or verify_purchase_cost
    candidates = []
    reused = 0
    for row in rows:
        key = (str(row.get("lank") or row.get("url") or ""), str(row.get("titel") or row.get("title") or ""))
        with _DETAIL_LOCK:
            cached = _DETAIL_CACHE.get(key)
        if cached and time.time() - cached[0] < 900:
            row.update(cached[1])
            reused += 1
            continue
        parsed = parse_card_features(str(row.get("titel") or row.get("title") or ""))
        title_number = parsed.get("card_number") or build_research_title_identity(str(row.get("titel") or row.get("title") or ""))["fields"].get("card_number")
        parts = urlsplit(str(row.get("lank") or row.get("url") or ""))
        if (parts.hostname in {"www.tradera.com", "tradera.com"}
                and re.match(r"/item/\d+/\d+(?:/|$)", parts.path)
                and parsed.get("player_name") and parsed.get("set_name")
                and not title_number and not parsed.get("is_lot")):
            candidates.append(row)
    # Give low entry costs the first chance; retain the rest for a later scan.
    candidates.sort(key=lambda row: float(row.get("pris") or row.get("price") or 999999))
    selected = candidates[:limit]
    recovered = sum(bool(row.get("description_research_identity")) for row in rows)
    checked = 0
    inactive = sum(bool(row.get("listing_inactive")) for row in rows)
    phase = "Läser saknade kortnummer från annonsbeskrivningar"
    begin_phase(phase, len(selected))
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(verifier, row): row for row in selected}
        for future in as_completed(futures):
            row = futures[future]
            try:
                row.update(future.result())
                fields = recover_description_identity(row)
                if fields.get("card_number"):
                    recovered += 1
                    row["description_research_identity"] = fields
                inactive += int(bool(row.get("listing_inactive")))
                if row.get("purchase_detail_verified"):
                    key = (str(row.get("lank") or row.get("url") or ""), str(row.get("titel") or row.get("title") or ""))
                    # Cache only primary listing fields, never analysis scores.
                    keys = ("full_description", "purchase_detail_verified", "purchase_detail_item_id",
                            "purchase_detail_url", "purchase_detail_title", "listing_inactive",
                            "description_research_identity")
                    with _DETAIL_LOCK:
                        _DETAIL_CACHE[key] = (time.time(), {key: row[key] for key in keys if key in row})
                        if len(_DETAIL_CACHE) > 1200:
                            oldest = min(_DETAIL_CACHE, key=lambda key: _DETAIL_CACHE[key][0])
                            _DETAIL_CACHE.pop(oldest, None)
            except Exception:
                # One malformed/offline ad must not lose the existing inventory.
                row["description_recovery_status"] = "UNAVAILABLE"
            checked += 1
            report_phase(phase, checked=checked, total=len(selected))
    return {"description_identity_candidates": len(candidates), "description_identity_checked": checked,
            "description_identity_reused": reused,
            "description_identity_recovered": recovered, "description_identity_inactive": inactive,
            "description_identity_remaining": max(0, len(candidates) - checked)}
