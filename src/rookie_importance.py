from __future__ import annotations

from typing import Any


def _norm(value: Any) -> str:
    return " ".join(str(value or "").casefold().replace("®", "").split())


PROGRAM_RULES = [
    {
        "patterns_any": ("young guns",),
        "sport": "hockey",
        "tier": "Flagship rookie",
        "base_score": 94,
        "reason": "Young Guns är ett centralt flagship-rookieprogram i Upper Decks årliga hockeyutgåvor.",
        "verification": "Verifiera exakt Young Guns-variant; bas, Clear Cut, Exclusives, High Gloss och Outburst är inte samma comp.",
    },
    {
        "patterns_any": ("future watch auto patch", "future watch autograph patch"),
        "sport": "hockey",
        "tier": "Premium rookie patch auto",
        "base_score": 97,
        "reason": "Future Watch Auto Patch är ett separat premium rookie patch-auto-program.",
        "verification": "Verifiera patch/auto-program, serial denominator och kortnummer före comp-sökning.",
    },
    {
        "patterns_any": ("future watch autograph", "future watch auto"),
        "sport": "hockey",
        "tier": "Premium rookie autograph",
        "base_score": 92,
        "reason": "Future Watch Autograph är ett etablerat rookie-autografprogram i SP Authentic.",
        "verification": "Jämför inte automatiskt med vanlig Future Watch eller Auto Patch-versioner.",
    },
    {
        "patterns_any": ("the cup rookie auto patch", "rookie auto patch"),
        "sport": "hockey",
        "tier": "High-end rookie patch auto",
        "base_score": 98,
        "reason": "Rookie Auto Patch i high-end-produkt är en separat premium rookie-identitet.",
        "verification": "Exakt produkt, patch/auto, serienummer och kortnummer måste matcha.",
    },
    {
        "patterns_any": ("rated rookie",),
        "sport": "football",
        "tier": "Recognized rookie program",
        "base_score": 78,
        "reason": "Rated Rookie är ett tydligt namngivet rookieprogram som bör separeras från vanliga basrookies.",
        "verification": "Verifiera produktfamilj och parallel; Rated Rookie förekommer i flera produktlinjer.",
    },
    {
        "patterns_all": ("topps chrome", "rookie"),
        "sport": "football",
        "tier": "Chrome rookie",
        "base_score": 84,
        "reason": "Topps Chrome-produktens baschecklistor lyfter fram rookies som en central del av produkten.",
        "verification": "Verifiera base/insert/parallel och kortnummer; Chrome-brandet räcker inte för exakt identitet.",
    },
    {
        "patterns_all": ("prizm", "rookie"),
        "sport": "football",
        "tier": "Prizm rookie",
        "base_score": 82,
        "reason": "Prizm-rookies bör hållas isär från inserts och färg-/nummerparalleller inom samma produktfamilj.",
        "verification": "Verifiera om kortet är base rookie eller en specifik Prizm-parallel/insertion.",
    },
    {
        "patterns_all": ("merlin", "rookie"),
        "sport": "football",
        "tier": "Secondary rookie program",
        "base_score": 70,
        "reason": "Merlin-rookies är ett separat rookieprogram, men ska inte automatiskt behandlas som spelarens viktigaste rookie.",
        "verification": "Sök exact sold comps innan programmet kallas spelarens nyckelrookie.",
    },
]


def _match_rule(text: str, sport: str | None) -> dict[str, Any] | None:
    sport_n = _norm(sport)
    best = None
    for rule in PROGRAM_RULES:
        if rule["sport"] and sport_n and rule["sport"] != sport_n:
            continue
        pats_all = tuple(_norm(p) for p in rule.get("patterns_all", ()))
        pats_any = tuple(_norm(p) for p in rule.get("patterns_any", rule.get("patterns", ())))
        all_ok = all(p in text for p in pats_all) if pats_all else True
        any_ok = any(p in text for p in pats_any) if pats_any else True
        if all_ok and any_ok:
            if best is None or int(rule["base_score"]) > int(best["base_score"]):
                best = rule
    return dict(best) if best else None


def build_player_rookie_importance(
    *,
    signals: list[dict] | None,
    features: dict | None,
    sport: str | None,
    player_name: str | None,
    player_market_score: int | float | None,
    sold_comparable_count: int | None,
    identity_confidence_score: int | float | None,
    valuation_confidence_score: int | float | None,
) -> dict[str, Any]:
    """Estimate how important a rookie *program identity* is worth investigating.

    This is not a value model and never declares a card to be a player's definitive
    rookie card. It only identifies strong rookie-program candidates and the evidence
    needed before that claim is safe.
    """
    features = features or {}
    rows = [dict(s) for s in (signals or []) if isinstance(s, dict)]
    text_parts = [str(features.get(k) or "") for k in ("rookie_program", "set_name", "parallel", "season", "year")]
    text_parts += [str(r.get("label") or "") for r in rows]
    text_parts += [str(r.get("program_family") or "") for r in rows]
    text_parts += [str(r.get("product_family") or "") for r in rows]
    text = _norm(" ".join(text_parts))

    is_rookie = bool(features.get("is_rookie")) or any(
        "rookie" in _norm(r.get("category")) or "rookie" in _norm(r.get("label"))
        for r in rows
    )
    if not is_rookie:
        return {
            "matched": False,
            "importance_score": 0,
            "tier": "Inte rookieidentifierat",
            "status": "Ingen rookiehierarki aktiverad",
            "reasons": [],
            "cautions": [],
            "next_action": None,
            "safe_to_call_key_rookie": False,
            "safe_for_valuation": False,
        }

    rule = _match_rule(text, sport)
    base = int(rule["base_score"]) if rule else 58
    player_score = max(0, min(100, int(round(float(player_market_score or 0)))))
    identity_conf = max(0, min(100, int(round(float(identity_confidence_score or 0)))))
    valuation_conf = max(0, min(100, int(round(float(valuation_confidence_score or 0)))))
    sold = max(0, int(sold_comparable_count or 0))

    # Program importance is mostly structural, with small evidence/player adjustments.
    importance = base * 0.72 + player_score * 0.12 + identity_conf * 0.10 + min(100, sold * 20) * 0.06
    if not player_name:
        importance = min(importance, 62)
    if identity_conf < 45:
        importance = min(importance, 64)
    importance = int(max(0, min(100, round(importance))))

    if importance >= 88:
        status = "Mycket stark rookie-kandidat att verifiera"
    elif importance >= 76:
        status = "Stark rookie-kandidat att verifiera"
    elif importance >= 62:
        status = "Relevant rookie-kandidat"
    else:
        status = "Sekundär/oklar rookie-kandidat"

    reasons: list[str] = []
    cautions: list[str] = []
    if rule:
        reasons.append(rule["reason"])
        cautions.append(rule["verification"])
    else:
        reasons.append("Kortet är rookieidentifierat men inget särskilt program har matchats mot rookie-kunskapsreglerna.")
        cautions.append("Kalla inte kortet spelarens nyckelrookie utan verifierat program och marknadsevidens.")
    if player_name:
        reasons.append(f"Spelarefterfrågan är {player_score}/100 för {player_name}.")
    if sold:
        reasons.append(f"{sold} verifierade sold comps finns i aktuellt underlag.")
    else:
        cautions.append("Inga verifierade sold comps finns i aktuellt underlag.")
    if identity_conf < 60:
        cautions.append("Kortidentiteten är för osäker för att slå fast rookieprogrammet definitivt.")

    # Deliberately very strict: 'key rookie' is only safe as a local evidence label,
    # never a universal hobby claim.
    safe_key = bool(
        rule
        and player_name
        and identity_conf >= 80
        and sold >= 3
        and valuation_conf >= 60
        and importance >= 80
    )
    tier = rule["tier"] if rule else "Rookie program – unclassified"
    if safe_key:
        key_label = "Starkt lokalt stöd för centralt rookieprogram"
        next_action = "Verifiera minst tre exact sold comps med samma program, variant och kortnummer innan köpbeslut."
    else:
        key_label = "Ej säkert att kalla spelarens nyckelrookie"
        next_action = "Verifiera exakt program/variant och sold comps; använd inte bara 'RC' eller rookie-text som bevis."

    return {
        "matched": True,
        "importance_score": importance,
        "tier": tier,
        "status": status,
        "key_rookie_status": key_label,
        "program_rule": rule,
        "player_score": player_score,
        "identity_confidence_score": identity_conf,
        "valuation_confidence_score": valuation_conf,
        "sold_comparable_count": sold,
        "reasons": reasons[:6],
        "cautions": list(dict.fromkeys(cautions))[:6],
        "next_action": next_action,
        "safe_to_call_key_rookie": safe_key,
        "safe_for_valuation": False,
        "note": (
            "Player Rookie Importance Engine prioriterar rookieprogram för verifiering. "
            "Den får inte skapa marknadsvärde, vinst, ROI eller maxbud och slår inte fast ett universellt 'true rookie card'."
        ),
    }
