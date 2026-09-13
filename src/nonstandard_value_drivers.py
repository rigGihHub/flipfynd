"""Non-standard collector value drivers.

Research layer for value drivers that are not captured by the usual rookie/
autograph/patch/serial-number logic. This module NEVER creates a price or buy
signal. It surfaces documented/possible narrative and anomaly drivers that
should trigger targeted research.
"""
from __future__ import annotations
import re
from src.oddity_registry import match_curated_cards, classify_listing_text, ODDITY_TAXONOMY


def _norm(v):
    return re.sub(r"[^a-z0-9]+", " ", str(v or "").casefold()).strip()


# Curated examples where hobby demand can be driven by an error, background
# detail or cultural story rather than conventional premium-card structure.
# These entries are intentionally narrow: matching the catalog creates a
# research lead, not a valuation claim.
KNOWN_STORY_CARDS = [
    {
        "sport": "basketball",
        "season": "1990-91",
        "set_tokens": ("hoops",),
        "card_number": "205",
        "player_tokens": ("mark", "jackson"),
        "driver": "Kulturell/bakgrundshistoria",
        "research": "Kontrollera varianten där Lyle och Erik Menendez syns i bakgrunden.",
        "key": "mark_jackson_menendez_background",
    },
    {
        "sport": "baseball",
        "season": "1989",
        "set_tokens": ("fleer",),
        "card_number": "381",
        "player_tokens": ("randy", "johnson"),
        "driver": "Bildvariation/censur",
        "research": "Kontrollera Marlboro-skyltens exakta variant; flera censureringsversioner finns.",
        "key": "randy_johnson_marlboro",
    },
    {
        "sport": "baseball",
        "season": "1989",
        "set_tokens": ("fleer",),
        "card_number": "616",
        "player_tokens": ("billy", "ripken"),
        "driver": "Tryck-/censurvariation",
        "research": "Kontrollera bat-knob-varianten; original och flera korrigeringsversioner finns.",
        "key": "billy_ripken_error",
    },
    {
        "sport": "baseball",
        "season": "1990",
        "set_tokens": ("topps",),
        "card_number": "414",
        "player_tokens": ("frank", "thomas"),
        "driver": "Extremt knapp tryckvariation",
        "research": "Kontrollera NNOF/No Name on Front mot verifierade referensbilder och gradingdata.",
        "key": "frank_thomas_nnof",
    },
]

GENERAL_DRIVER_RULES = [
    ("error", "Feltryck/error", "Verifiera att felet är en erkänd och knapp variant; många 'errors' saknar premie."),
    ("misprint", "Feltryck/error", "Verifiera korrigerad vs okorrigerad version och faktisk knapphet."),
    ("wrong photo", "Fel foto", "Verifiera om fel foto korrigerades och om båda versionerna är dokumenterade."),
    ("reverse negative", "Bildfel/reverse negative", "Verifiera erkänd bildvariation och population."),
    ("no name", "Saknad tryckinformation", "Verifiera att det är en dokumenterad produktionsvariant, inte slitage."),
    ("nnof", "Saknad tryckinformation", "Verifiera NNOF mot etablerade referensbilder."),
    ("marlboro", "Bakgrunds-/censurvariation", "Verifiera exakt censureringsvariant."),
    ("menendez", "Kulturell/bakgrundshistoria", "Verifiera rätt kort och att efterfrågan faktiskt finns i SOLD-data."),
    ("photo variation", "Bildvariation", "Verifiera vilken bildvariant som är korttryckt."),
    ("variation", "Produktvariation", "Verifiera att variationen är officiellt/dokumenterat avvikande och knapp."),
    ("first card", "Historisk förstautgåva", "Verifiera om detta verkligen är spelarens/ligans/produktens första kort."),
    ("pre rookie", "Pre-rookie/tidig utgåva", "Verifiera hobbydefinition och efterfrågan; pre-rookie är inte automatiskt dyrt."),
    ("test issue", "Test-/promo-utgåva", "Verifiera distribution, upplaga och autenticitet."),
    ("promo", "Promo/test", "Verifiera om promon är officiell och hur den distribuerades."),
    ("prototype", "Prototyp", "Verifiera proveniens och att kortet är en erkänd prototyp."),
    ("sample", "Sample/provtryck", "Verifiera officiellt sample och faktisk knapphet."),
]


def _field(features, *keys):
    for k in keys:
        v=features.get(k)
        if v not in (None, ""):
            return str(v)
    return ""


def build_nonstandard_value_profile(*, title="", sport="", player_name="", features=None):
    features=dict(features or {})
    hay=_norm(" ".join([
        title,
        player_name,
        _field(features,"set_name"),
        _field(features,"season","year"),
        _field(features,"card_number"),
        _field(features,"parallel"),
        _field(features,"variant"),
        _field(features,"notes"),
    ]))
    sport_n=_norm(sport)
    season=_norm(_field(features,"season","year"))
    set_n=_norm(_field(features,"set_name"))
    num=re.sub(r"^#", "", _field(features,"card_number").strip())
    player_n=_norm(player_name or features.get("player_name"))

    signals=[]
    known=[]
    curated_matches = match_curated_cards(title=title, sport=sport, player_name=player_name, features=features)
    for row in curated_matches:
        known.append(row["key"])
        signals.append({
            "type": ODDITY_TAXONOMY.get(row["category"], row["category"]),
            "reason": row["research"],
            "confidence": "KNOWN_CARD_MATCH",
            "registry_title": row.get("title"),
            "category": row.get("category"),
        })

    for token,label,research in GENERAL_DRIVER_RULES:
        if token in hay:
            signals.append({"type": label, "reason": research, "confidence": "LISTING_CLAIM"})

    for category in classify_listing_text(hay):
        label = ODDITY_TAXONOMY.get(category, category)
        if not any(sig.get("category") == category or sig.get("type") == label for sig in signals):
            signals.append({"type": label, "reason": "Annonsen innehåller språk som motiverar riktad oddity/variant-research.", "confidence": "LISTING_CLAIM", "category": category})

    # Other value mechanisms worth checking even without title keywords. These
    # are research prompts only and carry no automatic score/premium.
    research_prompts=[
        "Historisk eller kulturell bild: ovanlig person/händelse i bakgrunden, ikoniskt ögonblick eller foto som senare fick en egen historia.",
        "Korrigerad/okorrigerad produktion: fel namn, fel foto, reverse negative, saknad text, censur eller tydlig tryckändring mellan print runs.",
        "Extrem condition rarity: vanligt kort som är ovanligt svårt i hög grade på grund av centrering, yta, mörka kanter eller produktionsfel.",
        "Låg population trots hög tryckvolym: verklig pop-rarity kan vara viktigare än nominell upplaga.",
        "Tidiga/udda utgåvor: test issue, promo, prototype, regional, team issue, food issue, magazine insert eller pre-rookie.",
        "Proveniens: dokumenterad koppling till spelare, lag, berömd samling eller historiskt event kan skapa separat premium.",
        "Ikonisk design/foto/setstatus: första året av en viktig produkt, legendarisk setdesign eller hobby-definierande bild.",
        "Crossover-efterfrågan: kortet kan samlas av andra skäl än sporten, t.ex. popkultur, true crime, reklam/censur eller annan historisk kontext.",
        "Marknadschock/narrativ: dödsfall, rekord, Hall of Fame, comeback, dokumentär eller viral händelse kan ändra efterfrågan – ofta tillfälligt och måste bevisas i färska SOLD.",
        "Variant utan uppenbar märkning: factory set-only, glossy, Tiffany, O-Pee-Chee/Topps-variant, regional print eller andra distributionsskillnader.",
        "Särskild serienummer-estetik: jersey-number, first/last off the line eller annan samlarpreferens kan ge premium men måste styrkas av comps.",
        "Komplett kontext: en till synes vanlig basversion kan vara nyckelkort i master set, registry set eller svår komplett-checklistposition.",
    ]
    # Signals are useful for research, but must never create price confidence.
    score=min(35, len(known)*20 + sum(6 if s["confidence"]=="LISTING_CLAIM" else 0 for s in signals))
    return {
        "signal_score": score,
        "signals": signals[:8],
        "known_story_matches": known,
        "research_prompts": research_prompts,
        "requires_external_verification": bool(signals),
        "safe_for_valuation": False,
        "creates_market_value": False,
        "creates_buy_decision": False,
        "note": "Ovanliga värdedrivare är researchsignaler, inte prisbevis. Premie måste verifieras mot exakt variant, population och SOLD-comps.",
    }
