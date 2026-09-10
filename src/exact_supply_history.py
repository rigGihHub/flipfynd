"""Exact Supply History.

Persists factual snapshots of confirmed exact active-supply observations.
History is descriptive only: it never creates valuation, max price, BUY or a
synthetic scarcity score.
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path

from src.exact_card_supply import exact_identity_key


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _identity_id(item):
    key=exact_identity_key(item)
    if key is None:
        return None
    return "||".join(key)


def build_snapshot(target, confirmation_report, *, observed_at=None):
    identity_id=_identity_id(target)
    if identity_id is None:
        return {
            "ready":False,
            "status":"IDENTITY_NOT_READY",
            "creates_value":False,
            "creates_buy_decision":False,
        }
    report=confirmation_report or {}
    if not report.get("ready"):
        return {
            "ready":False,
            "status":"CONFIRMATION_NOT_READY",
            "creates_value":False,
            "creates_buy_decision":False,
        }

    return {
        "ready":True,
        "status":"OK",
        "identity_id":identity_id,
        "observed_at":observed_at or _now_iso(),
        "confirmed_exact":int(report.get("confirmed_exact") or 0),
        "possible":int(report.get("possible") or 0),
        "wrong_card":int(report.get("wrong_card") or 0),
        "creates_value":False,
        "creates_buy_decision":False,
        "creates_max_price":False,
    }


def load_history(path):
    path=Path(path)
    if not path.exists():
        return []
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [row for row in data if isinstance(row,dict)] if isinstance(data,list) else []


def save_snapshot(path, snapshot, *, max_rows=1000):
    if not (snapshot or {}).get("ready"):
        return 0
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    rows=load_history(path)
    rows.append({
        k:v for k,v in snapshot.items()
        if k not in {"ready","status","creates_value","creates_buy_decision","creates_max_price"}
    })
    rows=rows[-max(1,int(max_rows)):]
    path.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
    return len(rows)


def history_for_target(target, rows):
    identity_id=_identity_id(target)
    if identity_id is None:
        return []
    filtered=[r for r in (rows or []) if r.get("identity_id")==identity_id]
    return sorted(filtered,key=lambda r:str(r.get("observed_at") or ""))


def summarize_history(target, rows, *, minimum_snapshots=2):
    history=history_for_target(target,rows)
    if len(history)<max(2,int(minimum_snapshots)):
        return {
            "status":"OTILLRÄCKLIG_HISTORIK",
            "snapshots":len(history),
            "direction":"EJ_BEDÖMBAR",
            "change":None,
            "creates_value":False,
            "creates_buy_decision":False,
        }

    first=int(history[0].get("confirmed_exact") or 0)
    latest=int(history[-1].get("confirmed_exact") or 0)
    change=latest-first
    if change<0:
        direction="MINSKAT_OBSERVERAT_UTBUD"
    elif change>0:
        direction="ÖKAT_OBSERVERAT_UTBUD"
    else:
        direction="OFÖRÄNDRAT_OBSERVERAT_UTBUD"

    return {
        "status":"OK",
        "snapshots":len(history),
        "first_confirmed_exact":first,
        "latest_confirmed_exact":latest,
        "change":change,
        "direction":direction,
        "first_observed_at":history[0].get("observed_at"),
        "latest_observed_at":history[-1].get("observed_at"),
        "creates_value":False,
        "creates_buy_decision":False,
        "creates_max_price":False,
        "note":"Riktningen beskriver endast observerade bekräftade exact-supply-snapshots i FlipFynd.",
    }
