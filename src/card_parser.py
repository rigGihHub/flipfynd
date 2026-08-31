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


def extract_year(title: str) -> Optional[int]:
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


def detect_parallel(norm: str) -> Optional[str]:
    patterns = [
        "gold",
        "red",
        "blue",
        "green",
        "rainbow",
        "pink",
        "purple",
        "orange",
        "silver",
        "retro",
        "exclusive",
        "speckle",
        "outburst",
        "high gloss",
    ]

    for pattern in patterns:
        if re.search(rf"\b{re.escape(pattern)}\b", norm):
            return pattern.title()

    return None



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

def parse_card_features(title: str) -> dict:
    norm = normalize_text(title)
    serial_number = extract_serial_number(title)
    set_name = extract_set_name(title)
    player_name = extract_player_name(title)
    grade = extract_grade(title)
    grading_company = extract_grading_company(title)

    rookie_variant, rookie_tier = detect_rookie_variant(norm, set_name)
    is_rookie = rookie_variant is not None
    is_auto = bool(re.search(r"\bauto\b|\bautograph\b|\bautograf\b|\bsigned\b|\bsignature\b", norm))
    is_patch = "patch" in norm
    is_jersey = "jersey" in norm or "memorabilia" in norm
    is_game_worn = "game worn" in norm or "game-used" in norm or "game used" in norm
    is_graded = grade is not None or any(x in norm for x in ["psa", "bgs", "sgc"])
    is_lot = "samling" in norm or "lot" in norm or "collection" in norm

    return {
        "normalized_title": norm,
        "player_name": player_name,
        "set_name": set_name,
        "year": extract_year(title),
        "parallel": detect_parallel(norm),
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
        "serial_number": serial_number,
        "is_low_serial": serial_number is not None and serial_number <= 50,
        "is_mid_serial": serial_number is not None and 51 <= serial_number <= 199,
        "is_high_serial": serial_number is not None and serial_number >= 200,
        "is_1of1": serial_number == 1,
    }