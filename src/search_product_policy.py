"""Resale search scope, separate from authenticity and valuation evidence."""
import re
import unicodedata

from src.card_parser import parse_card_features

POLICY_VERSION = "football-hobby-v2"
EXCLUDED_PRODUCT_LABEL = "Match Attax och Adrenalyn är uteslutna, även Limited Edition och numrerade varianter."


def _containers(item):
    if not isinstance(item, dict):
        return []
    return [item] + [item[key] for key in ("source_item", "_source_item") if isinstance(item.get(key), dict)]


def _norm(text):
    return re.sub(r"[^\w]+", " ", unicodedata.normalize("NFKC", str(text)).casefold()).strip()


def product_scope(item, sport=None):
    containers = _containers(item)
    if isinstance(item, str):
        containers = [{"title": item}]
    product_text = []
    for row in containers:
        product_text.extend(str(row.get(key) or "") for key in (
            "titel", "title", "set_name", "product_name", "series_name", "card_identity_family"))
        for key in ("exact_identity_gate_identity_fields", "exact_identity_gate_research_identity_fields"):
            fields = row.get(key)
            if isinstance(fields, dict):
                product_text.append(str(fields.get("set_name") or ""))
    text = _norm(" ".join(product_text))
    if re.search(r"\bmatch\s*attax\b", text):
        return {"allowed": False, "reason": "EXCLUDED_MATCH_ATTAX", "product": "Match Attax"}
    if re.search(r"\badrenal(?:yn|in)(?:\s*xl)?\b", text):
        return {"allowed": False, "reason": "EXCLUDED_ADRENALYN", "product": "Adrenalyn"}
    categories = _norm(" ".join(str(row.get(key) or "") for row in containers
                                for key in ("sport", "source_category", "category_name", "category")))
    football = str(sport or "").casefold() in {"football", "fotboll"} or bool(
        re.search(r"\b(?:football|fotboll|soccer|premier league|uefa|fifa)\b", categories + " " + text))
    # Marketplace categories can be wrong. Explicit product sport names must
    # override a soccer category; otherwise a numbered tennis card ranks as a
    # football hobby variant in restored results as well as fresh searches.
    if football and re.search(r"\b(?:tennis|basketball|baseball|hockey|nhl|nba|nfl|mlb|ufc|nascar|wwe|formula 1|formel 1)\b", text):
        return {"allowed": False, "reason": "NON_FOOTBALL_PRODUCT", "product": "kort från annan sport"}
    # Beast Mode also exists outside Match Attax. Do not misidentify the product
    # or ban a genuinely numbered/autograph variant of a hobby collection.
    # Manufacturer context: investor.fanatics.com, Premier League launch 2025-07-17.
    ordinary_insert = re.search(r"\bbeast\s+mode\b", text) and (
        football or re.search(r"\btopps\b.*\bbm\s*\d+\b", text))
    if ordinary_insert:
        title = next((row.get("titel") or row.get("title") for row in containers
                      if row.get("titel") or row.get("title")), "")
        features = parse_card_features(str(title))
        if not any(features.get(key) for key in ("serial_number", "is_auto", "is_patch", "is_jersey")):
            return {"allowed": False, "reason": "STANDARD_FOOTBALL_INSERT", "product": "Beast Mode utan verifierbar specialvariant"}
    return {"allowed": True, "reason": None, "product": None}


def filter_search_products(rows, sport=None):
    allowed, reasons = [], {}
    for row in rows or []:
        scope = product_scope(row, sport)
        if scope["allowed"]:
            allowed.append(row)
        else:
            reason = scope["reason"]
            reasons[reason] = reasons.get(reason, 0) + 1
    return allowed, reasons


def football_card_priority(item):
    """Research tiebreak only; never prices a card or promotes a BUY."""
    rows = _containers(item)
    text = _norm(" ".join(str(row.get(key) or "") for row in rows
                          for key in ("titel", "title", "sport", "source_category", "set_name")))
    if not re.search(r"\b(?:football|fotboll|soccer|premier league|uefa|fifa)\b", text):
        return 0
    title = next((row.get("titel") or row.get("title") for row in rows if row.get("titel") or row.get("title")), "")
    fields = parse_card_features(str(title))
    if any(fields.get(key) for key in ("serial_number", "is_auto", "is_patch", "is_jersey")):
        return 2
    if re.search(r"\b(?:chrome|finest|prizm|select|merlin|obsidian|museum|immaculate|impeccable)\b", text):
        return 1
    return 0
