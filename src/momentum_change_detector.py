"""Evidence-only change detector for player momentum snapshots.

Detects observed changes between timestamped snapshots for the same player and
metric. It does not score talent, infer causality, or create buy decisions.
"""
from __future__ import annotations
from datetime import datetime, timezone


def _dt(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def normalize_snapshot(row):
    row = dict(row or {})
    player = str(row.get("player_name") or "").strip()
    metric = str(row.get("metric") or row.get("metric_name") or "").strip()
    source = str(row.get("source_name") or "").strip()
    source_url = str(row.get("source_url") or "").strip()
    observed = _dt(row.get("observed_at"))
    value = row.get("value")
    if not player or not metric or not source or not source_url or not observed or value is None:
        return {"status": "REJECTED", "reason": "missing_or_invalid_evidence"}
    return {
        "status": "READY",
        "player_name": player,
        "sport": row.get("sport"),
        "metric": metric,
        "value": value,
        "unit": row.get("unit"),
        "observed_at": observed.isoformat(),
        "source_name": source,
        "source_url": source_url,
    }


def _numeric_delta(before, after):
    try:
        if isinstance(before, bool) or isinstance(after, bool):
            return None
        return float(after) - float(before)
    except (TypeError, ValueError):
        return None


def detect_momentum_changes(snapshots):
    valid = []
    rejected = 0
    for row in snapshots or []:
        normalized = normalize_snapshot(row)
        if normalized["status"] == "READY":
            valid.append(normalized)
        else:
            rejected += 1

    grouped = {}
    for row in valid:
        key = (row["player_name"].casefold(), row["metric"].casefold())
        grouped.setdefault(key, []).append(row)

    changes = []
    for rows in grouped.values():
        rows.sort(key=lambda x: x["observed_at"])
        for before, after in zip(rows, rows[1:]):
            if before["value"] == after["value"]:
                continue
            changes.append({
                "player_name": after["player_name"],
                "sport": after.get("sport") or before.get("sport"),
                "metric": after["metric"],
                "before": before["value"],
                "after": after["value"],
                "delta": _numeric_delta(before["value"], after["value"]),
                "unit": after.get("unit") or before.get("unit"),
                "from_observed_at": before["observed_at"],
                "to_observed_at": after["observed_at"],
                "before_source_name": before["source_name"],
                "before_source_url": before["source_url"],
                "after_source_name": after["source_name"],
                "after_source_url": after["source_url"],
                "buy_signal_created": False,
                "interpretation": None,
            })

    changes.sort(key=lambda x: (x["to_observed_at"], x["player_name"], x["metric"]), reverse=True)
    return {
        "status": "READY" if changes else "INSUFFICIENT_DATA",
        "snapshot_count": len(valid),
        "rejected_count": rejected,
        "change_count": len(changes),
        "changes": changes,
        "note": "Visar observerade före/efter-förändringar. Ingen talangscore, prognos eller köp-signal skapas.",
    }
