import re
from typing import Optional

from src.player_market import get_all_player_names, normalize_player_name


KNOWN_PLAYERS = [name.casefold() for name in get_all_player_names()]


SET_PATTERNS = [
    ("the cup", "The Cup"),
    ("sp authentic", "SP Authentic"),
    ("ultimate collection", "Ultimate Collection"),
    ("ultimate", "Ultimate Collection"),
    ("dominion", "Dominion"),
    ("premier", "Premier"),
    ("credentials", "Credentials"),
    ("engrained", "Engrained"),
    ("allure", "Allure"),
    ("stature", "Stature"),
    ("young guns", "Young Guns"),
    ("canvas", "Canvas"),
    ("opc platinum", "OPC Platinum"),
    ("o pee chee platinum", "OPC Platinum"),
    ("o-pee-chee platinum", "OPC Platinum"),
    ("o pee chee", "O-Pee-Chee"),
    ("o-pee-chee", "O-Pee-Chee"),
    ("parkhurst", "Parkhurst"),
    ("artifacts", "Artifacts"),
    ("black diamond", "Black Diamond"),
    ("ice", "Ice"),
    ("mvp", "MVP"),
    ("trilogy", "Trilogy"),
    ("sp game used", "SP Game Used"),
    ("spa", "SP Authentic"),
    ("topps chrome sapphire", "Topps Chrome Sapphire"),
    ("topps chrome", "Topps Chrome"),
    ("topps finest", "Topps Finest"),
    ("merlin chrome", "Topps Merlin"),
    ("topps merlin", "Topps Merlin"),
    ("panini prizm", "Panini Prizm"),
    ("prizm", "Panini Prizm"),
    ("panini select", "Panini Select"),
    ("topps museum", "Topps Museum"),
    ("museum collection", "Topps Museum"),
    ("obsidian", "Obsidian"),
    ("immaculate", "Immaculate"),
    ("national treasures", "National Treasures"),
    ("donruss optic", "Donruss Optic"),
    ("optic", "Donruss Optic"),
    ("skybox metal universe", "Metal Universe"),
    ("metal universe", "Metal Universe"),
    ("skybox metal", "Metal Universe"),
    ("donruss", "Donruss"),
    ("upper deck", "Upper Deck"),
]


CARD_STOPWORDS = {
    "upper",
    "deck",
    "ud",
    "opc",
    "o",
    "pee",
    "chee",
    "the",
    "cup",
    "sp",
    "authentic",
    "allure",
    "canvas",
    "rookie",
    "young",
    "guns",
    "series",
    "hockey",
    "kort",
    "card",
    "cards",
    "auto",
    "autograph",
    "autograf",
    "patch",
    "jersey",
    "mint",
    "condition",
    "parallel",
    "blue",
    "red",
    "green",
    "gold",
    "silver",
    "violet",
    "retro",
    "future",
    "watch",
    "stature",
    "engrained",
    "credentials",
    "premier",
    "portraits",
    "portrait",
    "team",
    "canada",
    "leaf",
    "parkhurst",
    "score",
    "fleer",
    "insert",
    "prizm",
    "numbered",
    "world",
    "tour",
    "ice",
    "platinum",
    "mvp",
    "edition",
    "retail",
    "hobby",
    "blaster",
    "exclusive",
    "psa",
    "bgs",
    "sgc",
    "lot",
    "collection",
    "samling",
}


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = str(text).lower()
    text = text.replace("\u00a0", " ").replace("\u202f", " ")
    text = re.sub(r"[/]", " / ", text)
    text = re.sub(r"[\(\)\[\]#,.:;!?]", " ", text)
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_player_name(title: str) -> Optional[str]:
    norm = normalize_text(title)

    for player in KNOWN_PLAYERS:
        if player in norm:
            return normalize_player_name(player.title())

    tokens = norm.split()
    candidates = []

    for token in tokens:
        if token in CARD_STOPWORDS:
            continue
        if re.search(r"\d", token):
            continue
        if len(token) <= 1:
            continue
        if not re.fullmatch(r"[a-zåäö'`]+", token):
            continue
        candidates.append(token)

    if len(candidates) >= 2:
        return f"{candidates[0].title()} {candidates[1].title()}"

    return None


def extract_set_name(title: str) -> Optional[str]:
    norm = normalize_text(title)

    for raw_pattern, display_name in SET_PATTERNS:
        if raw_pattern in norm:
            return display_name

    if re.search(r"\bud\s+young\s+guns\b", norm):
        return "Young Guns"

    return None


def extract_season(title: str) -> Optional[str]:
    """Normalize common card-season formats to ``YYYY-YY``.

    Examples: ``2023-24``, ``2023/24`` and ``2023/2024`` all become
    ``2023-24``. A short form such as ``23/24`` is only accepted when the
    title also contains a recognizable card product/set, reducing the risk of
    mistaking a serial number for a season.
    """
    raw = str(title or "")

    # Full start year + short/full end year.
    match = re.search(r"\b((?:19|20)\d{2})\s*[-/]\s*((?:19|20)?\d{2})\b", raw)
    if match:
        start = int(match.group(1))
        end_raw = match.group(2)
        end = int(end_raw) if len(end_raw) == 4 else (start // 100) * 100 + int(end_raw)
        if end == start + 1:
            return f"{start}-{end % 100:02d}"

    # Short form is common in listings, but also resembles serial numbering.
    # Require a known product/set and consecutive years before accepting it.
    short = re.search(r"(?<!\d)(\d{2})\s*[-/]\s*(\d{2})(?!\d)", raw)
    if short and extract_set_name(raw):
        start2, end2 = int(short.group(1)), int(short.group(2))
        if (end2 - start2) % 100 == 1:
            start = 2000 + start2 if start2 <= 79 else 1900 + start2
            return f"{start}-{end2:02d}"

    return None


def extract_year(title: str) -> Optional[int]:
    season = extract_season(title)
    if season:
        return int(season[:4])

    norm = normalize_text(title)
    match = re.search(r"\b(19|20)\d{2}\b", norm)
    if match:
        return int(match.group(0))
    return None


def extract_serial_number(title: str) -> Optional[int]:
    raw = str(title or "")
    norm = normalize_text(raw)

    if "1/1" in raw.lower() or "1 1" in norm:
        return 1

    match = re.search(r"/(\d{1,4})\b", raw)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None

    return None


def extract_card_number(title: str) -> Optional[str]:
    """Extract a checklist/card number without confusing it with serial numbering.

    Supported conservative forms include ``#451``, ``Card #451``, ``No. 451`` and
    alphanumeric checklist numbers such as ``#YG-23``. Numbered print runs such
    as ``12/99`` or ``1/1`` are deliberately excluded.
    """
    raw = str(title or "")

    # Explicit hash notation is the strongest signal. Reject a value that is
    # immediately part of a print-run fraction (e.g. #12/99).
    hash_match = re.search(r"(?<![\w/])#\s*([A-Za-z]{1,5}[- ]?\d{1,4}|\d{1,4})(?!\s*/\s*\d)", raw)
    if hash_match:
        value = re.sub(r"\s+", "", hash_match.group(1)).upper()
        return value

    # Card/No. wording is also sufficiently explicit, but bare numbers are not.
    labelled = re.search(
        r"\b(?:card|kort|no\.?|nr\.?)\s*(?:#\s*)?([A-Za-z]{1,5}[- ]?\d{1,4}|\d{1,4})(?!\s*/\s*\d)",
        raw,
        flags=re.IGNORECASE,
    )
    if labelled:
        value = re.sub(r"\s+", "", labelled.group(1)).upper()
        # Do not let a four-digit year masquerade as a checklist number.
        if value.isdigit() and 1900 <= int(value) <= 2099:
            return None
        return value

    return None


def extract_grade(title: str) -> Optional[str]:
    norm = normalize_text(title)

    grade_patterns = [
        # PSA titles often include GEM MINT / GEM MT between company and grade.
        ("PSA", r"\bpsa(?:\s+(?:gem\s+mint|gem\s+mt|mint|nm[- ]?mt))?\s*(10|9|8|7|6)\b"),
        ("BGS", r"\bbgs\s*(10|9\.5|9|8\.5|8|7\.5|7)\b"),
        ("SGC", r"\bsgc\s*(10|9\.5|9|8\.5|8|7\.5|7)\b"),
    ]

    for company, pattern in grade_patterns:
        match = re.search(pattern, norm)
        if match:
            return f"{company} {match.group(1)}"

    return None


def extract_grading_company(title: str) -> Optional[str]:
    norm = normalize_text(title)
    for company in ("PSA", "BGS", "SGC"):
        if re.search(rf"\b{company.lower()}\b", norm):
            return company
    return None



def detect_lot_info(text: str) -> dict:
    """Detect multi-card listings conservatively.

    Avoids treating product names such as ``Ultimate Collection`` or
    ``Museum Collection`` as card lots. Explicit quantities and bundle wording
    are stronger signals than the word ``collection`` by itself.
    """
    raw = str(text or "")
    norm = normalize_text(raw)

    # Product names where "collection" is part of the official set name.
    product_collection = bool(re.search(
        r"\b(?:ultimate|museum)\s+collection\b", norm
    ))

    quantity_patterns = [
        r"\b(\d{1,3})\s*(?:st(?:\.|ycken)?\s*)?(?:kort|cards?)\b",
        r"\b(?:lot|paket|bundle)\s*(?:of|med)?\s*(\d{1,3})\b",
        r"\b(\d{1,3})\s*[x×]\s*(?:kort|cards?)?\b",
    ]
    lot_count = None
    for pattern in quantity_patterns:
        match = re.search(pattern, norm, flags=re.IGNORECASE)
        if match:
            try:
                count = int(match.group(1))
            except (TypeError, ValueError):
                continue
            if 2 <= count <= 500:
                lot_count = count
                break

    strong_terms = bool(re.search(
        r"\b(?:kortlot|card\s+lot|mixed\s+lot|team\s+lot|bundle|kortpaket|paket\s+med\s+kort|samling\s+av\s+kort|collection\s+of\s+cards?)\b",
        norm,
    ))
    generic_lot = bool(re.search(r"\b(?:lot|samling)\b", norm))
    collection_lot = bool(re.search(r"\bcollection\b", norm)) and not product_collection

    is_lot = bool(lot_count or strong_terms or generic_lot or collection_lot)
    confidence = "low"
    if lot_count or strong_terms:
        confidence = "high"
    elif generic_lot:
        confidence = "medium"
    elif collection_lot:
        confidence = "low"

    return {
        "is_lot": is_lot,
        "lot_count": lot_count,
        "lot_confidence": confidence if is_lot else "none",
    }

def detect_parallel_info(norm: str) -> tuple[Optional[str], str, str]:
    """Detect named card parallels without treating every colour word as a parallel.

    Returns ``(name, tier, confidence)``. The hierarchy is intentionally coarse and
    is used as a valuation guardrail rather than a price guide. Standalone team
    colours such as ``Red Wings`` must not become false premium signals.
    """
    text = norm or ""

    # Highly distinctive names first.
    patterns = [
        (r"\bgold\s+outburst\b", "Gold Outburst", "elite", "high"),
        (r"\bred\s+outburst\b", "Red Outburst", "elite", "high"),
        (r"\bsilver\s+outburst\b", "Silver Outburst", "rare", "high"),
        (r"\boutburst\b", "Outburst", "rare", "high"),
        (r"\b(?:precious\s+metal\s+gems?|pmg)\s+gold\b", "PMG Gold", "elite", "high"),
        (r"\b(?:precious\s+metal\s+gems?|pmg)\s+green\b", "PMG Green", "elite", "high"),
        (r"\b(?:precious\s+metal\s+gems?|pmg)\s+red\b", "PMG Red", "rare", "high"),
        (r"\bemerald\s+surge\b", "Emerald Surge", "elite", "high"),
        (r"\borange\s+checkers\b", "Orange Checkers", "elite", "high"),
        (r"\bseismic\s+gold\b", "Seismic Gold", "rare", "high"),
        (r"\bviolet\s+pixels\b", "Violet Pixels", "strong", "high"),
        (r"\bhigh\s+gloss\b", "High Gloss", "elite", "high"),
        (r"\bgold\s+vinyl\b", "Gold Vinyl", "elite", "high"),
        (r"\bblack\s+finite\b", "Black Finite", "elite", "high"),
        (r"\bclear\s+cut\b", "Clear Cut", "rare", "high"),
        (r"\bexclusives?\b", "Exclusive", "rare", "high"),
        (r"\bcracked\s+ice\b", "Cracked Ice", "rare", "high"),
        (r"\bice\s+prizm\b", "Ice Prizm", "strong", "high"),
        (r"\bspeckle\b", "Speckle", "strong", "high"),
        (r"\bmojo\b", "Mojo", "strong", "high"),
        (r"\bshimmer\b", "Shimmer", "strong", "high"),
        (r"\bpulsar\b", "Pulsar", "strong", "high"),
        (r"\bx[- ]?fractor\b", "X-Fractor", "strong", "high"),
        (r"\brefractor\b", "Refractor", "strong", "high"),
        (r"\brainbow\b", "Rainbow", "strong", "high"),
    ]
    for pattern, name, tier, confidence in patterns:
        if re.search(pattern, text):
            return name, tier, confidence

    # Silver is a recognized parallel name in several major products.
    if re.search(r"\bsilver\b", text):
        return "Silver", "strong", "medium"

    # Bare colour words are too ambiguous. Only accept them when the title itself
    # gives card-variant context (parallel/prizm/wave/shimmer/refractor).
    colour_names = {
        "gold": ("Gold", "rare"),
        "orange": ("Orange", "strong"),
        "red": ("Red", "strong"),
        "blue": ("Blue", "standard"),
        "green": ("Green", "standard"),
        "pink": ("Pink", "standard"),
        "purple": ("Purple", "standard"),
    }
    context = r"(?:parallel|prizm|refractor|wave|shimmer|pulsar|mojo|speckle)"
    for colour, (name, tier) in colour_names.items():
        if re.search(rf"\b{colour}\b(?:\s+\w+){{0,2}}\s+{context}\b", text) or re.search(
            rf"\b{context}\b(?:\s+\w+){{0,2}}\s+{colour}\b", text
        ):
            return name, tier, "medium"

    return None, "none", "low"


def detect_parallel(norm: str) -> Optional[str]:
    return detect_parallel_info(norm)[0]



def detect_rookie_variant(norm: str, set_name: Optional[str] = None) -> tuple[Optional[str], str]:
    """Identify named rookie programs separately from a generic RC label.

    The tier is intentionally coarse: ``iconic`` for established flagship rookie
    programs, ``strong`` for recognizable rookie inserts/lines and ``standard``
    for a generic rookie label. It is used as a guardrail, not as a price guide.
    """
    text = norm or ""

    # Hockey rookie programs. Order matters: specific variants before parent set.
    if re.search(r"\byoung\s+guns\s+canvas\b|\bcanvas\s+young\s+guns\b", text):
        return "Young Guns Canvas", "strong"
    if re.search(r"\bfuture\s+watch\s+(?:auto|autograph|autograf)\b|\bfwa\b", text):
        return "Future Watch Auto", "iconic"
    if re.search(r"\bfuture\s+watch\b", text):
        return "Future Watch", "strong"
    if set_name == "Young Guns" or re.search(r"\byoung\s+guns\b|\byoungguns\b", text):
        return "Young Guns", "iconic"
    if re.search(r"\bmarquee\s+rookie(?:s)?\b", text):
        return "Marquee Rookie", "strong"

    # Football/soccer rookie programs. These are useful signals, but still need
    # player demand and comps; a brand name alone must not create a large premium.
    if re.search(r"\brated\s+rookie\b", text):
        return "Rated Rookie", "strong"
    if (set_name == "Panini Prizm" or "prizm" in text) and re.search(r"\b(?:rookie|rc)\b", text):
        return "Prizm Rookie", "strong"
    if set_name == "Topps Chrome" and re.search(r"\b(?:rookie|rc)\b", text):
        return "Topps Chrome Rookie", "strong"
    if set_name == "Topps Merlin" and re.search(r"\b(?:rookie|rc)\b", text):
        return "Merlin Rookie", "strong"
    if set_name == "Panini Select" and re.search(r"\b(?:rookie|rc)\b", text):
        return "Select Rookie", "strong"

    if re.search(r"\b(?:rookie|rc)\b", text):
        return "Generic Rookie", "standard"

    return None, "none"



def build_card_identity(features: dict) -> dict:
    """Build a conservative normalized identity for comp matching.

    The identity joins product/program, rookie program and named parallel into one
    card concept so e.g. ``Young Guns Outburst`` is not treated as just another
    Young Guns card. It deliberately avoids inventing missing card numbers or
    unverified variants from free text.
    """
    features = features or {}
    set_name = features.get("set_name")
    rookie_variant = features.get("rookie_variant")
    parallel = features.get("parallel")
    year = features.get("year")
    season = features.get("season")
    card_number = features.get("card_number")

    family = None
    if rookie_variant and rookie_variant != "Generic Rookie":
        family = rookie_variant
    elif set_name:
        family = set_name
    elif features.get("is_rookie"):
        family = "Generic Rookie"

    parts = []
    if season:
        parts.append(str(season))
    elif year:
        parts.append(str(year))
    if family:
        parts.append(str(family))
    if parallel:
        parts.append(str(parallel))
    if card_number:
        parts.append(f"#{card_number}")
    if features.get("is_auto"):
        parts.append("Auto")
    if features.get("is_patch"):
        parts.append("Patch")
    if features.get("grade"):
        parts.append(str(features.get("grade")))

    display = " • ".join(parts) if parts else None
    key = "|".join(str(part).casefold().strip() for part in parts) if parts else None

    # Exact identity is only high-confidence when the product/program itself is
    # known. A bare RC + colour word remains too weak for aggressive comps.
    if family and family != "Generic Rookie" and card_number:
        confidence = "high"
    elif family and family != "Generic Rookie" and parallel:
        confidence = "high"
    elif family and family != "Generic Rookie":
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "card_identity": display,
        "card_identity_key": key,
        "card_identity_family": family,
        "card_identity_confidence": confidence,
    }

def parse_card_features(title: str) -> dict:
    norm = normalize_text(title)
    serial_number = extract_serial_number(title)
    card_number = extract_card_number(title)
    set_name = extract_set_name(title)
    player_name = extract_player_name(title)
    grade = extract_grade(title)
    grading_company = extract_grading_company(title)

    rookie_variant, rookie_tier = detect_rookie_variant(norm, set_name)
    parallel, parallel_tier, parallel_confidence = detect_parallel_info(norm)
    is_rookie = rookie_variant is not None
    is_auto = bool(re.search(r"\bauto\b|\bautograph\b|\bautograf\b|\bsigned\b|\bsignature\b", norm))
    is_patch = "patch" in norm
    is_jersey = "jersey" in norm or "memorabilia" in norm
    is_game_worn = "game worn" in norm or "game-used" in norm or "game used" in norm
    is_graded = grade is not None or any(x in norm for x in ["psa", "bgs", "sgc"])
    lot_info = detect_lot_info(title)
    is_lot = lot_info["is_lot"]

    features = {
        "normalized_title": norm,
        "player_name": player_name,
        "set_name": set_name,
        "year": extract_year(title),
        "season": extract_season(title),
        "parallel": parallel,
        "parallel_tier": parallel_tier,
        "parallel_confidence": parallel_confidence,
        "is_rookie": is_rookie,
        "rookie_variant": rookie_variant,
        "rookie_tier": rookie_tier,
        "is_auto": is_auto,
        "is_patch": is_patch,
        "is_jersey": is_jersey,
        "is_game_worn": is_game_worn,
        "is_graded": is_graded,
        "grade": grade,
        "grading_company": grading_company,
        "is_lot": is_lot,
        "lot_count": lot_info.get("lot_count"),
        "lot_confidence": lot_info.get("lot_confidence", "none"),
        "serial_number": serial_number,
        "card_number": card_number,
        "is_low_serial": serial_number is not None and serial_number <= 50,
        "is_mid_serial": serial_number is not None and 51 <= serial_number <= 199,
        "is_high_serial": serial_number is not None and serial_number >= 200,
        "is_1of1": serial_number == 1,
    }
    features.update(build_card_identity(features))
    return features