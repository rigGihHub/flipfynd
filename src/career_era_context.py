"""Verified Career & Era Context; never infer missing metadata."""
from __future__ import annotations

LABELS={
 "active_young_star":"Aktiv ung stjärna",
 "active_star":"Aktiv stjärna",
 "active_superstar":"Aktiv superstjärna",
 "active_legend":"Aktiv legend",
 "retired_legend":"Pensionerad legend",
}
ERA_LABELS={"modern":"Modern era","late_1970s_1990s":"Sent 1970-tal–1990-tal"}

def build_career_era_context(*, player_name, context=None, is_rookie=False, lifecycle=None):
    context=dict(context or {})
    verified=bool(context.get("career_context_verified"))
    status=context.get("career_status") if verified else None
    era=context.get("era") if verified else None
    reasons=[]; cautions=[]
    if status:
        reasons.append(f"Verifierad karriärkontext: {LABELS.get(status,status)}.")
    if era:
        reasons.append(f"Era: {ERA_LABELS.get(era,era)}.")
    if not verified:
        cautions.append("Karriärstatus/era saknar verifierad metadata och lämnas därför okänd.")
    if lifecycle and lifecycle.get("derived"):
        reasons.append(f"Livscykel: {lifecycle.get('label')}" + (f" ({lifecycle.get('age')} år)." if lifecycle.get("age") is not None else "."))
    if is_rookie and status=="retired_legend":
        reasons.append("Rookie-kort av en pensionerad legend är historisk rookie-kontext, inte prospect-kontext.")
    elif is_rookie and status in {"active_young_star","active_star","active_superstar"}:
        reasons.append("Rookie-kortet kopplas till en aktiv spelares verifierade karriärkontext.")
    return {
      "career_status":status,
      "career_status_label":LABELS.get(status) if status else None,
      "era":era,
      "era_label":ERA_LABELS.get(era) if era else None,
      "verified":verified,
      "source":context.get("career_context_source") if verified else None,
      "source_url":context.get("career_context_source_url") if verified else None,
      "activity_status":context.get("activity_status") if verified else None,
      "position":context.get("position") if verified else None,
      "team":context.get("team") if verified else None,
      "date_of_birth":context.get("date_of_birth") if verified else None,
      "lifecycle_stage":(lifecycle or {}).get("stage"),
      "lifecycle_label":(lifecycle or {}).get("label"),
      "age":(lifecycle or {}).get("age"),
      "reasons":reasons,
      "cautions":cautions,
      "safe_for_valuation":False,
      "creates_market_value":False,
      "creates_buy_decision":False,
      "note":"Career & Era Context ger samlarhistorik. Den får inte ensam skapa pris, ROI eller KÖP."
    }
