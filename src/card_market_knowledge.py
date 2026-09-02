import json
from functools import lru_cache
from pathlib import Path

from src.card_parser import normalize_text

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "card_market_knowledge.json"


@lru_cache(maxsize=1)
def load_card_market_knowledge() -> dict:
    try:
        with DATA_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {"signals": [], "sources": [], "version": None}
    if not isinstance(data, dict):
        return {"signals": [], "sources": [], "version": None}
    data.setdefault("signals", [])
    data.setdefault("sources", [])
    return data


def detect_market_knowledge_signals(text: str, sport: str | None = None) -> list[dict]:
    """Recognize authoritative chase/rarity terminology without assigning value.

    The knowledge base intentionally carries *no price multipliers*. A signal can
    help identify what a listing claims to be, but only sold/market evidence may
    establish monetary value.
    """
    norm = normalize_text(text)
    wanted_sport = str(sport or "").casefold().strip()
    found = []
    for signal in load_card_market_knowledge().get("signals", []):
        signal_sport = str(signal.get("sport") or "").casefold()
        if wanted_sport and signal_sport and signal_sport != wanted_sport:
            continue
        patterns = [normalize_text(p) for p in signal.get("patterns", []) if p]
        patterns_all = [normalize_text(p) for p in signal.get("patterns_all", []) if p]
        patterns_any = [normalize_text(p) for p in signal.get("patterns_any", []) if p]
        legacy_ok = (not patterns) or all(pattern in norm for pattern in patterns)
        all_ok = (not patterns_all) or all(pattern in norm for pattern in patterns_all)
        any_ok = (not patterns_any) or any(pattern in norm for pattern in patterns_any)
        has_rule = bool(patterns or patterns_all or patterns_any)
        if has_rule and legacy_ok and all_ok and any_ok:
            found.append({
                "label": signal.get("label"),
                "category": signal.get("category"),
                "rarity_signal": signal.get("rarity_signal"),
                "confidence": signal.get("confidence", "medium"),
                "print_run": signal.get("print_run"),
                "attention_priority": int(signal.get("attention_priority", 0) or 0),
                "source_id": signal.get("source_id"),
                "product_family": signal.get("product_family"),
                "program_family": signal.get("program_family"),
                "importance_reason": signal.get("importance_reason"),
                "knowledge_tier": signal.get("knowledge_tier"),
            })
    return found


def market_knowledge_attention(signals: list[dict] | None) -> dict:
    """Return a conservative *analysis priority*, never a price premium.

    This can move a listing into the small full-analysis pool so rare/important
    structures are less likely to be missed by the cheap fast pass. It must not
    alter resale value, profit, max bid or the final rank directly.
    """
    signals = list(signals or [])
    if not signals:
        return {"score": 0, "level": "normal", "reason": None}
    top = max((int(s.get("attention_priority", 0) or 0) for s in signals), default=0)
    score_map = {1: 2, 2: 5, 3: 10, 4: 18, 5: 28}
    score = score_map.get(max(0, min(5, top)), 0)
    level = "mycket hög" if top >= 5 else "hög" if top >= 4 else "förhöjd" if top >= 3 else "normal"
    labels = [str(s.get("label")) for s in signals if s.get("label")]
    reason = f"Känd kortstruktur att granska: {', '.join(labels[:3])}" if labels else None
    return {"score": score, "level": level, "reason": reason}


def detect_market_attention(text: str, sport: str | None = None) -> dict:
    return market_knowledge_attention(detect_market_knowledge_signals(text, sport))
