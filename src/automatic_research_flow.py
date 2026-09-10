"""Automatic Research Flow.

Runs every research step that is deterministic and local, then collapses any
remaining human/external work into one next intervention. It never fabricates
identity, SOLD evidence, valuation, max price or BUY decisions.
"""
from __future__ import annotations

from src.research_action_center import build_research_actions, build_low_click_action_plan
from src.pressure_research_drilldown import build_pressure_drilldown
from src.exact_identity_gate import build_exact_identity_gate


AUTO_LOCAL_ACTIONS = {
    "REVIEW_VALUATION_EVIDENCE",
}
HUMAN_IDENTITY_ACTIONS = {
    "VERIFY_CARD_NUMBER",
    "VERIFY_SET",
    "VERIFY_SEASON",
    "VERIFY_PLAYER",
    "STRENGTHEN_IDENTITY",
    "VERIFY_PARALLEL",
    "VERIFY_SERIAL",
}
EXTERNAL_RESEARCH_ACTIONS = {
    "FIND_VERIFIED_SOLD",
    "CHECK_EXACT_SUPPLY",
    "REFRESH_EXACT_SUPPLY",
}


def build_automatic_research_flow(item, supply_history_rows, sold_records):
    """Return what FlipFynd can settle automatically and the one thing left.

    This function is intentionally side-effect free. "Automatic" means no extra
    user navigation for local checks; external API calls and human verification
    remain explicit.
    """
    item = dict(item or {})
    actions = build_research_actions(item, supply_history_rows, sold_records)
    drill = build_pressure_drilldown(item, supply_history_rows, sold_records)
    identity = build_exact_identity_gate(item)

    completed = [
        "Pressure-underlag analyserat",
        "Exact Identity Gate kontrollerad",
        "Befintliga verifierade SOLD kontrollerade",
        "Exact-supply-historik kontrollerad",
        "Värderingsblockerare kontrollerade",
    ]

    remaining = list(actions.get("actions") or [])
    human = [a for a in remaining if a.get("action_id") in HUMAN_IDENTITY_ACTIONS]
    external = [a for a in remaining if a.get("action_id") in EXTERNAL_RESEARCH_ACTIONS]
    local_review = [a for a in remaining if a.get("action_id") in AUTO_LOCAL_ACTIONS]

    # Local review actions don't require another button; the existing evidence is
    # already surfaced in drilldown and can be marked as automatically inspected.
    auto_resolved = []
    for action in local_review:
        auto_resolved.append({
            "action_id": action["action_id"],
            "label": action["label"],
            "result": "Underlaget har redan granskats lokalt; blockeraren kvarstår tills evidensen faktiskt förbättras.",
        })

    if human:
        intervention = {
            "type":"HUMAN_VERIFICATION",
            "label":"Verifiera kortidentiteten",
            "reason":"Minst en identitetsuppgift kräver mänsklig kontroll innan FlipFynd kan fortsätta säkert.",
            "actions":human,
        }
    elif external:
        first = external[0]
        intervention = {
            "type":"EXTERNAL_RESEARCH",
            "label":first["label"],
            "reason":first["reason"],
            "actions":[first],
        }
    else:
        intervention = None

    return {
        "status":"WAITING_FOR_ONE_INTERVENTION" if intervention else "AUTO_CHECKS_COMPLETE",
        "auto_completed":completed,
        "auto_resolved":auto_resolved,
        "next_intervention":intervention,
        "remaining_action_count":len(human)+len(external),
        "identity_supports_exact_comp_search":bool(identity.get("supports_exact_comp_search")),
        "pressure_status":drill.get("pressure_status"),
        "creates_identity":False,
        "creates_sold_evidence":False,
        "creates_value":False,
        "creates_buy_decision":False,
        "creates_max_price":False,
        "note":"FlipFynd gör alla säkra lokala kontroller automatiskt och stannar bara där verifiering eller extern research faktiskt behövs.",
    }
