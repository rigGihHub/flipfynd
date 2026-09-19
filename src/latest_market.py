"""Bounded latest-listing discovery without discarding the saved archive."""
from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

LATEST_MAX_PAGES = 5


def newest_first_url(url):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["sortBy"] = "AddedOn"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def latest_analysis_items(items):
    """Use the latest newest-first snapshot per sport; legacy data is a fallback.

    A fetch timestamp is discovery provenance, not the listing's publication
    date. Each snapshot stays bounded even when old page-1 rows remain saved.
    """
    rows = list(items or [])
    latest = {}
    for row in rows:
        if row.get("discovery_sort") != "AddedOn" or not row.get("latest_scan_at"):
            continue
        category = row.get("source_category") or "unknown"
        latest[category] = max(latest.get(category, ""), row["latest_scan_at"])
    selected=[row for row in rows if (row.get("source_category") or "unknown") not in latest
            or (row.get("discovery_sort") == "AddedOn"
                and row.get("latest_scan_at") == latest[row.get("source_category") or "unknown"])]
    # Latest scans are fetched with sortBy=AddedOn and pages are persisted in
    # crawl order. Preserve that ordering explicitly for opportunity-first use.
    return sorted(selected, key=lambda row: (
        str(row.get("latest_scan_at") or ""),
        -int(row.get("sida") or 9999),
    ), reverse=True)
