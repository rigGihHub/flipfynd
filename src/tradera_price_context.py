"""Exact active asking comparisons from freshly scanned Tradera inventory."""
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlsplit

from src.analysis_scope import _listing_key
from src.asking_price_opportunity import asking_research_identity, build_asking_price_opportunity
from src.ebay_browse_context import match_active_rows


def _fresh_timestamp(item, now):
    # Unstamped/archive-only listings cannot be treated as current offers.
    raw = item.get("latest_scan_at") or item.get("fetched_at")
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return None
        return dt.isoformat() if 0 <= (now - dt).total_seconds() <= 86400 else None
    except (ValueError, TypeError):
        return None


def screen_tradera_prices(targets, market, *, now=None):
    now = now or datetime.now(timezone.utc)
    index = defaultdict(list)
    for item in market:
        timestamp = _fresh_timestamp(item, now)
        text = " ".join(str(item.get(key) or "") for key in ("sale_type", "raw_text", "titel")).casefold()
        # Auction opening/current bids do not establish a fixed comparison price.
        if not timestamp or "köp nu" not in text or item.get("sold") or item.get("ended"):
            continue
        url = item.get("lank") or item.get("url") or ""
        host = urlsplit(str(url)).hostname or ""
        if host not in {"tradera.com", "www.tradera.com"}:
            continue
        identity = asking_research_identity(item)
        number = str(identity.get("card_number") or "").casefold()
        if not number:
            continue
        index[number].append((item, timestamp))
    results, seen = [], set()
    checked, usable = 0, 0
    for item in targets:
        key = _listing_key(item)
        if key in seen or not _fresh_timestamp(item, now):
            continue
        seen.add(key)
        identity = asking_research_identity(item)
        if not (identity.get("player_name") and identity.get("card_number")
                and (identity.get("season") or identity.get("set_name"))):
            continue
        raw = []
        for comp, timestamp in index.get(str(identity["card_number"]).casefold(), []):
            if _listing_key(comp) == key:
                continue
            # Keep comparison item prices separate from the target's acquisition freight.
            raw.append({"title": comp.get("titel") or comp.get("title"), "price": comp.get("pris"),
                        "currency": "SEK", "url": comp.get("lank") or comp.get("url"),
                        "source": "Tradera", "buying_options": ["FIXED_PRICE"],
                        "fetched_at": timestamp})
        checked += 1
        rows = match_active_rows(raw, identity)
        context = {"rows": rows, "raw_listing_count": len(raw),
                   "fetched_at": min((row["fetched_at"] for row in rows), default=None)}
        scenario = build_asking_price_opportunity(item, context)
        usable += bool(scenario.get("comparison_count"))
        if scenario.get("net_margin", 0) >= 1:
            scenario["source_label"] = "Tradera"
            results.append({**item, "asking_price_opportunity": scenario})
    results.sort(key=lambda row: row["asking_price_opportunity"]["net_margin"], reverse=True)
    return results, {"tradera_price_checked": checked, "tradera_price_usable": usable,
                     "tradera_possible_finds": sum(bool(row["asking_price_opportunity"].get("possible_find")) for row in results)}
