"""Controlled learning layer for the curated oddity registry.

The purpose is to discover *candidate* knowledge-base entries from repeated,
evidence-rich research signals without ever mutating the curated registry at
runtime. A proposal must be reviewed by a human/developer before it can become
a registry seed.
"""
from __future__ import annotations

from collections import defaultdict
import re

from src.oddity_registry import CURATED_ODDITY_CARDS


def _norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _first(item, *keys):
    for key in keys:
        value = item.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _card_identity(item):
    features = dict(item.get("features") or item.get("card_features") or {})
    return {
        "sport": _norm(_first(item, "sport", "category") or features.get("sport")),
        "season": _norm(_first(item, "season", "year") or features.get("season") or features.get("year")),
        "set_name": _norm(_first(item, "set_name", "set") or features.get("set_name")),
        "card_number": re.sub(r"^#", "", str(_first(item, "card_number", "number") or features.get("card_number") or "").strip()),
        "player": _norm(_first(item, "player_name", "player") or features.get("player_name")),
    }


def _already_curated(identity):
    player_tokens = tuple(identity["player"].split())
    for row in CURATED_ODDITY_CARDS:
        if row.get("card_number") and str(row["card_number"]) != identity["card_number"]:
            continue
        if row.get("season") and _norm(row["season"]) != identity["season"]:
            continue
        if row.get("sport") and row["sport"] not in identity["sport"]:
            continue
        if row.get("set_tokens") and not all(tok in identity["set_name"] for tok in row["set_tokens"]):
            continue
        row_player = tuple(row.get("player_tokens") or ())
        if row_player and not all(tok in player_tokens for tok in row_player):
            continue
        return True
    return False


def _identity_strength(item, identity):
    explicit = bool(
        item.get("exact_identity_verified")
        or item.get("exact_comp_identity_ready")
        or item.get("decision_strong_identity")
        or item.get("identity_ready")
    )
    anchors = sum(bool(identity[k]) for k in ("player", "season", "set_name", "card_number"))
    return explicit, anchors


def _sold_evidence(item):
    count = int(_num(_first(item, "exact_sold_comps", "sold_comps", "verified_sold_count"), 0))
    groups = int(_num(_first(item, "sold_source_groups", "source_group_count", "comp_source_groups"), 0))
    return count, groups


def _oddity_categories(item):
    categories=[]
    for signal in item.get("nonstandard_value_signals") or []:
        if not isinstance(signal, dict):
            continue
        category = str(signal.get("category") or signal.get("type") or "").strip()
        if category:
            categories.append(category)
    return list(dict.fromkeys(categories))


def _fingerprint(identity, categories):
    if not (identity["player"] and identity["card_number"]):
        return ""
    category = _norm(categories[0] if categories else "oddity")
    return "|".join([
        identity["sport"], identity["season"], identity["set_name"],
        identity["card_number"], identity["player"], category,
    ])


def build_registry_proposal_queue(items, limit=10):
    """Build reviewable registry proposals from repeated/evidence-rich signals.

    Safety rules:
    - never mutates CURATED_ODDITY_CARDS
    - never creates a valuation, SOLD comp or BUY decision
    - existing curated cards are excluded
    - one noisy listing is not enough for REVIEW_READY
    """
    grouped=defaultdict(list)
    for item in items or []:
        if not isinstance(item, dict):
            continue
        categories=_oddity_categories(item)
        if not categories:
            continue
        identity=_card_identity(item)
        if _already_curated(identity):
            continue
        fingerprint=_fingerprint(identity, categories)
        if not fingerprint:
            continue
        grouped[fingerprint].append((item, identity, categories))

    proposals=[]
    for fingerprint, rows in grouped.items():
        item, identity, categories = rows[0]
        occurrences=len(rows)
        exact_any=False
        anchors_max=0
        sold_max=0
        source_groups_max=0
        checklist=False
        image_verified=False
        reasons=[]
        urls=[]
        for row, ident, cats in rows:
            explicit, anchors=_identity_strength(row, ident)
            exact_any = exact_any or explicit
            anchors_max=max(anchors_max, anchors)
            sold, groups=_sold_evidence(row)
            sold_max=max(sold_max, sold)
            source_groups_max=max(source_groups_max, groups)
            checklist = checklist or bool(row.get("checklist_verified") or row.get("checklist_match_verified"))
            image_verified = image_verified or bool(row.get("image_variant_verified") or row.get("visual_variant_verified"))
            url=row.get("url")
            if url and url not in urls:
                urls.append(url)

        evidence=[]
        if exact_any:
            evidence.append("exact identity verifierad")
        elif anchors_max >= 4:
            evidence.append("4 identitetsankare")
        elif anchors_max >= 3:
            evidence.append("3 identitetsankare")
        if occurrences >= 2:
            evidence.append(f"återkommer i {occurrences} annonser")
        if sold_max >= 2:
            evidence.append(f"{sold_max} verifierade exact SOLD")
        if source_groups_max >= 2:
            evidence.append(f"SOLD från {source_groups_max} källgrupper")
        if checklist:
            evidence.append("checklistreferens verifierad")
        if image_verified:
            evidence.append("bild/variant visuellt verifierad")

        # REVIEW_READY requires repeated observation plus either strong identity
        # and market/checklist evidence. No single field can promote by itself.
        strong_identity = exact_any or anchors_max >= 4
        corroboration = (sold_max >= 2) or checklist or image_verified or source_groups_max >= 2
        review_ready = occurrences >= 2 and strong_identity and corroboration

        if review_ready:
            status="REVIEW_READY"
            action="Granska källor och skriv en kuraterad registry-post manuellt."
        elif occurrences >= 2 and strong_identity:
            status="NEEDS_CORROBORATION"
            action="Hämta checklist-/variantbevis eller minst två exact SOLD innan registry-förslag."
        else:
            status="NEEDS_EVIDENCE"
            action="Samla fler oberoende observationer och stärk exakt identitet först."

        priority = min(100, int(
            occurrences * 14
            + (24 if exact_any else anchors_max * 4)
            + min(20, sold_max * 7)
            + min(12, source_groups_max * 6)
            + (10 if checklist else 0)
            + (8 if image_verified else 0)
        ))

        title = str(_first(item, "titel", "title") or f"{identity['player']} #{identity['card_number']}")
        proposals.append({
            "fingerprint": fingerprint,
            "title": title,
            "player": identity["player"],
            "season": identity["season"],
            "set_name": identity["set_name"],
            "card_number": identity["card_number"],
            "categories": categories[:5],
            "occurrences": occurrences,
            "status": status,
            "priority_score": priority,
            "evidence": evidence,
            "action": action,
            "urls": urls[:3],
            "research_only": True,
            "auto_add_allowed": False,
            "creates_market_value": False,
            "creates_buy_decision": False,
            "creates_sold_comp": False,
        })

    status_rank={"REVIEW_READY":3, "NEEDS_CORROBORATION":2, "NEEDS_EVIDENCE":1}
    proposals.sort(key=lambda p:(status_rank[p["status"]], p["priority_score"], p["occurrences"]), reverse=True)
    return {
        "rows": proposals[:max(0, int(limit))],
        "review_ready_count": sum(1 for p in proposals if p["status"]=="REVIEW_READY"),
        "proposal_count": len(proposals),
        "auto_mutates_registry": False,
        "note": "FlipFynd får föreslå nya kunskapsbasposter men aldrig lägga till dem automatiskt. Varje post kräver manuell källgranskning.",
    }
