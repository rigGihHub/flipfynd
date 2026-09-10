"""Research Action Center.

Turns existing Pressure Research blockers into concrete next research actions.
Actions are workflow guidance only: they do not create identity facts, SOLD
records, valuations, max prices, scores, or BUY decisions.
"""
from __future__ import annotations

from src.pressure_research_drilldown import build_pressure_drilldown
from src.exact_identity_gate import build_exact_identity_gate


def _action(action_id, label, reason, priority):
    return {
        "action_id": action_id,
        "label": label,
        "reason": reason,
        "priority": priority,
        "creates_identity": False,
        "creates_sold_evidence": False,
        "creates_value": False,
        "creates_buy_decision": False,
        "creates_max_price": False,
    }


def build_research_actions(item, supply_history_rows, sold_records):
    item = dict(item or {})
    drill = build_pressure_drilldown(item, supply_history_rows, sold_records)
    identity = build_exact_identity_gate(item)
    actions = []

    missing = set(identity.get("missing_fields") or [])
    blockers = " ".join(str(x) for x in (identity.get("blockers") or [])).casefold()

    if not identity.get("supports_exact_comp_search"):
        if "card_number" in missing:
            actions.append(_action(
                "VERIFY_CARD_NUMBER",
                "Verifiera kortnummer",
                "Exakt kortnummer saknas i den strukturerade identiteten.",
                10,
            ))
        if "set_name" in missing:
            actions.append(_action(
                "VERIFY_SET",
                "Verifiera set/produkt",
                "Set eller produktnamn saknas i den exakta identiteten.",
                10,
            ))
        if "season" in missing:
            actions.append(_action(
                "VERIFY_SEASON",
                "Verifiera säsong/år",
                "Säsong eller år saknas i den exakta identiteten.",
                9,
            ))
        if "player_name" in missing or "player" in blockers:
            actions.append(_action(
                "VERIFY_PLAYER",
                "Verifiera spelare",
                "Spelaridentiteten är inte tillräckligt säker för exact-comp-sökning.",
                10,
            ))
        if not actions:
            actions.append(_action(
                "STRENGTHEN_IDENTITY",
                "Stärk kortidentiteten",
                "Exact Identity Gate är inte tillräckligt stark trots att grundfälten kan finnas.",
                10,
            ))

    sold_count = int(item.get("sold_comparable_count") or 0)
    if sold_count < 2:
        needed = 2 - sold_count
        label = "Hitta 1 verifierad SOLD till" if needed == 1 else f"Hitta {needed} verifierade SOLD"
        actions.append(_action(
            "FIND_VERIFIED_SOLD",
            label,
            f"Nu finns {sold_count} matchande verifierade SOLD; minst 2 krävs för beslutsstarkt värdeunderlag.",
            8,
        ))

    if not drill.get("supply_snapshots"):
        actions.append(_action(
            "CHECK_EXACT_SUPPLY",
            "Kontrollera exact supply",
            "Ingen sparad exact-supply-observation finns för kortet.",
            7,
        ))
    elif len(drill.get("supply_snapshots") or []) < 2:
        actions.append(_action(
            "REFRESH_EXACT_SUPPLY",
            "Ta en ny exact-supply snapshot",
            "Minst två observationer behövs för att se en faktisk förändring över tid.",
            7,
        ))

    if not bool(item.get("valuation_display_safe")) and sold_count >= 2:
        actions.append(_action(
            "REVIEW_VALUATION_EVIDENCE",
            "Granska värderingsunderlaget",
            "Verifierade SOLD finns, men värderingen är fortfarande inte säker nog för visning.",
            6,
        ))

    if item.get("parallel") in (None, "") and bool(item.get("is_parallel")):
        actions.append(_action(
            "VERIFY_PARALLEL",
            "Verifiera parallel/variant",
            "Kortet är markerat som parallel men variantnamnet saknas.",
            10,
        ))

    if item.get("serial_denominator") in (None, "") and bool(item.get("is_serial_numbered")):
        actions.append(_action(
            "VERIFY_SERIAL",
            "Verifiera numrering",
            "Kortet är markerat som numrerat men serienämnaren saknas.",
            10,
        ))

    # Deduplicate by action id and keep deterministic highest-priority ordering.
    unique = {}
    for action in actions:
        unique.setdefault(action["action_id"], action)
    actions = sorted(unique.values(), key=lambda x: (-int(x["priority"]), x["action_id"]))

    next_action = actions[0] if actions else None
    return {
        "actions": actions,
        "count": len(actions),
        "next_action": next_action,
        "status": "ACTION_NEEDED" if actions else "NO_ACTION_FROM_CHECKED_GAPS",
        "creates_new_score": False,
        "creates_identity": False,
        "creates_sold_evidence": False,
        "creates_value": False,
        "creates_buy_decision": False,
        "creates_max_price": False,
        "note": (
            "Research Action Center prioriterar bara nästa kontroll utifrån redan kända luckor. "
            "En utförd åtgärd måste fortfarande ge verifierat underlag innan något ändras i analysen."
        ),
    }

def build_low_click_action_plan(item, supply_history_rows, sold_records):
    """Collapse many research gaps into one primary workflow.

    The plan does not execute external research or mutate evidence. It merely
    groups already-derived actions so the UI can stay one-click-first.
    """
    center = build_research_actions(item, supply_history_rows, sold_records)
    actions = list(center.get("actions") or [])
    if not actions:
        return {
            "status":"NO_ACTION",
            "primary":None,
            "remaining_count":0,
            "creates_buy_decision":False,
            "creates_value":False,
        }

    ids={a.get("action_id") for a in actions}
    identity_ids={"VERIFY_CARD_NUMBER","VERIFY_SET","VERIFY_SEASON","VERIFY_PLAYER",
                  "STRENGTHEN_IDENTITY","VERIFY_PARALLEL","VERIFY_SERIAL"}
    if ids & identity_ids:
        primary={
            "workflow_id":"IDENTITY_WORKFLOW",
            "label":"Fixa kortidentiteten",
            "reason":"Samla identitetskontrollerna i ett enda steg innan prisresearch.",
            "action_ids":[a["action_id"] for a in actions if a.get("action_id") in identity_ids],
        }
    elif "FIND_VERIFIED_SOLD" in ids:
        primary={
            "workflow_id":"SOLD_WORKFLOW",
            "label":next(a["label"] for a in actions if a.get("action_id")=="FIND_VERIFIED_SOLD"),
            "reason":"Nästa viktigaste steg är verifierat SOLD-underlag.",
            "action_ids":["FIND_VERIFIED_SOLD"],
        }
    elif ids & {"CHECK_EXACT_SUPPLY","REFRESH_EXACT_SUPPLY"}:
        aid="CHECK_EXACT_SUPPLY" if "CHECK_EXACT_SUPPLY" in ids else "REFRESH_EXACT_SUPPLY"
        action=next(a for a in actions if a.get("action_id")==aid)
        primary={
            "workflow_id":"SUPPLY_WORKFLOW",
            "label":action["label"],
            "reason":action["reason"],
            "action_ids":[aid],
        }
    else:
        action=actions[0]
        primary={
            "workflow_id":"REVIEW_WORKFLOW",
            "label":action["label"],
            "reason":action["reason"],
            "action_ids":[action["action_id"]],
        }

    covered=set(primary["action_ids"])
    return {
        "status":"ACTION_NEEDED",
        "primary":primary,
        "remaining_count":sum(1 for a in actions if a.get("action_id") not in covered),
        "all_actions":actions,
        "creates_identity":False,
        "creates_sold_evidence":False,
        "creates_buy_decision":False,
        "creates_value":False,
        "creates_max_price":False,
        "note":"En huvudåtgärd visas först för att minimera knapptryckningar. Fler steg ligger bakom detaljer.",
    }
