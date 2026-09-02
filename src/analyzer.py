import re
import statistics

from src.card_parser import build_card_identity, detect_lot_info, parse_card_features
from src.card_market_knowledge import detect_market_knowledge_signals
from src.card_intelligence import build_card_intelligence
from src.card_knowledge_library import explain_library_match
from src.variant_hierarchy import build_variant_hierarchy
from src.collector_intelligence import build_collector_intelligence_matrix
from src.player_card_demand import build_player_card_demand
from src.valuable_card_knowledge import build_valuable_card_knowledge
from src.rookie_importance import build_player_rookie_importance
from src.mispriced_rookie_hunter import build_mispriced_rookie_signal
from src.misclassified_card_hunter import build_misclassified_card_signal
from src.detail_evidence_fusion import build_detail_evidence_fusion
from src.chase_knowledge_graph import build_chase_knowledge_graph
from src.visual_edge import build_visual_edge
from src.flip_scenarios import build_flip_scenarios
from src.comments import build_comment
from src.market_analysis import build_market_analysis
from src.player_market import get_player_database, match_player, normalize_player_name
from src.pricing import normalize_shipping, total_acquisition_cost


HOCKEY_SETS = {
    "Young Guns": 16,
    "The Cup": 18,
    "SP Authentic": 14,
    "Dominion": 10,
    "Ultimate Collection": 10,
    "Premier": 8,
    "Black Diamond": 8,
    "OPC Platinum": 7,
}


FOOTBALL_SETS = {
    "Topps Chrome": 16,
    "Topps Chrome Sapphire": 17,
    "Topps Finest": 12,
    "Topps Merlin": 13,
    "Panini Prizm": 15,
    "Panini Select": 12,
    "Topps Museum": 14,
    "Obsidian": 13,
    "Immaculate": 16,
    "National Treasures": 18,
    "Donruss Optic": 10,
    "Metal Universe": 11,
    "Donruss": 8,
}


HOCKEY_PREMIUM = {
    "The Cup",
    "SP Authentic",
    "Dominion",
    "Ultimate Collection",
    "Premier",
    "Black Diamond",
}


FOOTBALL_PREMIUM = {
    "Topps Chrome",
    "Topps Finest",
    "Topps Merlin",
    "Panini Prizm",
    "Panini Select",
    "Topps Museum",
    "Obsidian",
    "Immaculate",
    "National Treasures",
}


def normalize_name(name):
    return normalize_player_name(name)


def detect_known_player(title, sport):
    return match_player(title, sport).get('name')


def detect_player_match(title, sport):
    return match_player(title, sport)


def detect_set(
    title,
    sport,
):
    text = (
        title
        or ""
    ).casefold()

    aliases = {
        "Young Guns": [
            "young guns",
            "youngguns",
        ],
        "The Cup": [
            "the cup",
        ],
        "SP Authentic": [
            "sp authentic",
            "future watch",
        ],
        "Dominion": [
            "dominion",
        ],
        "Ultimate Collection": [
            "ultimate collection",
        ],
        "Premier": [
            "premier",
        ],
        "Black Diamond": [
            "black diamond",
        ],
        "OPC Platinum": [
            "opc platinum",
            "o-pee-chee platinum",
        ],
        "Topps Chrome": [
            "topps chrome",
        ],
        "Topps Finest": [
            "topps finest",
            "finest",
        ],
        "Topps Merlin": [
            "topps merlin",
            "merlin chrome",
            "merlin",
        ],
        "Panini Prizm": [
            "panini prizm",
            "prizm",
        ],
        "Panini Select": [
            "panini select",
            "select",
        ],
        "Topps Museum": [
            "topps museum",
            "museum collection",
        ],
        "Obsidian": [
            "obsidian",
        ],
        "Immaculate": [
            "immaculate",
        ],
        "National Treasures": [
            "national treasures",
        ],
        "Donruss": [
            "donruss",
            "optic",
        ],
    }

    available_sets = (
        FOOTBALL_SETS
        if sport == "football"
        else HOCKEY_SETS
    )

    for set_name in available_sets:
        needles = aliases.get(
            set_name,
            [
                set_name.casefold()
            ],
        )

        for needle in needles:
            if needle in text:
                return set_name

    return None


def contains_auto(text):
    return bool(
        re.search(
            r"\b("
            r"auto|"
            r"autograph|"
            r"autograf|"
            r"signed|"
            r"signature"
            r")\b",
            text or "",
            flags=re.IGNORECASE,
        )
    )


def extract_serial(title):
    match = re.search(
        r"(?<!\d)"
        r"(\d{1,4})/"
        r"(\d{1,4})"
        r"(?!\d)",
        title or "",
    )

    if not match:
        return (
            None,
            None,
        )

    return (
        int(match.group(1)),
        int(match.group(2)),
    )


def get_features(
    title,
    sport,
):
    features = dict(
        parse_card_features(
            title
        )
        or {}
    )

    player_match = detect_player_match(
        title,
        sport,
    )

    if player_match.get("name"):
        features["player_name"] = player_match["name"]
        features["player_match_confidence"] = player_match.get("confidence", "high")
        features["player_match_type"] = player_match.get("match_type", "exact")
    else:
        # Parserns fallback kan vara användbar som texttolkning, men den ska
        # inte behandlas som en säker marknadsidentifiering.
        features["player_name"] = normalize_name(features.get("player_name"))
        features["player_match_confidence"] = "low"
        features["player_match_type"] = "parser_fallback"

    detected_set = detect_set(
        title,
        sport,
    )

    if detected_set:
        features["set_name"] = (
            detected_set
        )

    _, serial_total = (
        extract_serial(
            title
        )
    )

    text = (
        title
        or ""
    ).lower()

    features["is_rookie"] = bool(
        features.get(
            "is_rookie"
        )
        or re.search(
            r"\b(rookie|rc)\b",
            text,
        )
    )

    features["is_auto"] = bool(
        features.get(
            "is_auto"
        )
        or contains_auto(
            text
        )
    )

    features["is_patch"] = bool(
        features.get(
            "is_patch"
        )
        or "patch" in text
        or "relic" in text
    )

    features["is_jersey"] = bool(
        features.get(
            "is_jersey"
        )
        or "jersey" in text
        or "memorabilia" in text
    )

    features["is_game_worn"] = bool(
        features.get(
            "is_game_worn"
        )
        or "game worn" in text
        or "game-worn" in text
        or "match worn" in text
    )

    features["is_1of1"] = bool(
        features.get(
            "is_1of1"
        )
        or "1/1" in text
    )

    if serial_total is not None:
        features[
            "serial_number"
        ] = serial_total

        features[
            "is_low_serial"
        ] = serial_total <= 50

        features[
            "is_mid_serial"
        ] = (
            51
            <= serial_total
            <= 199
        )

        features[
            "is_high_serial"
        ] = (
            serial_total >= 200
        )

    else:
        features.setdefault(
            "serial_number",
            None,
        )

        features.setdefault(
            "is_low_serial",
            False,
        )

        features.setdefault(
            "is_mid_serial",
            False,
        )

        features.setdefault(
            "is_high_serial",
            False,
        )

    features.setdefault(
        "year",
        None,
    )

    features.setdefault(
        "grade",
        None,
    )

    features.setdefault(
        "parallel",
        None,
    )

    lot_info = detect_lot_info(title)
    features.setdefault("is_lot", lot_info.get("is_lot", False))
    features.setdefault("lot_count", lot_info.get("lot_count"))
    features.setdefault("lot_confidence", lot_info.get("lot_confidence", "none"))

    features.update(build_card_identity(features))
    return features



def compute_identity_confidence_score(features):
    """Translate identity evidence into a conservative 0-100 evidence score."""
    features = features or {}
    score = 0
    pmc = str(features.get("player_match_confidence") or "low")
    if features.get("player_name") and pmc == "high":
        score += 24
    elif features.get("player_name") and pmc == "medium":
        score += 16
    elif features.get("player_name"):
        score += 6
    if features.get("set_name"):
        score += 20
    if features.get("season") or features.get("year"):
        score += 14
    if features.get("card_number"):
        score += 18
    if features.get("parallel"):
        score += 10 if features.get("parallel_confidence") == "high" else 6
    if features.get("rookie_variant") and features.get("rookie_variant") != "Generic Rookie":
        score += 5
    if features.get("grade"):
        score += 5
    if features.get("serial_number") is not None:
        score += 4
    conflicts = list(features.get("identity_conflicts") or [])
    if conflicts:
        score -= min(45, 18 + 12 * (len(conflicts) - 1))
    sources = features.get("identity_evidence_sources") or {}
    if any("listing_text" in vals for vals in sources.values() if isinstance(vals, list)):
        score += 3
    return max(0, min(100, round(score)))


def get_listing_features(item, sport):
    """Build identity from title plus safe evidence from the listing container.

    The title stays authoritative. Surrounding listing text may fill missing
    identifiers but never silently overwrite a conflicting title claim.
    """
    item = item or {}
    title = str(item.get("titel") or "")
    raw_text = str(item.get("raw_text") or "")
    full_description = str(item.get("full_description") or "")
    evidence_text = " ".join(part for part in (raw_text, full_description) if part).strip()
    title_features = dict(get_features(title, sport))
    raw_features = dict(get_features(evidence_text, sport)) if evidence_text and evidence_text != title else {}
    merged = dict(title_features)
    evidence, conflicts, enriched = {}, [], []
    identity_fields = [
        "player_name", "set_name", "season", "year", "card_number", "parallel",
        "rookie_variant", "grade", "grading_company", "serial_number",
    ]
    boolean_fields = ["is_rookie", "is_auto", "is_patch", "is_jersey", "is_game_worn", "is_graded", "is_1of1"]

    for field in identity_fields:
        tv, rv = title_features.get(field), raw_features.get(field)
        if tv not in (None, ""):
            evidence.setdefault(field, []).append("title")
        if rv not in (None, ""):
            evidence.setdefault(field, []).append("listing_text")
        if tv in (None, "") and rv not in (None, ""):
            merged[field] = rv
            enriched.append(field)
        elif tv not in (None, "") and rv not in (None, "") and tv != rv:
            conflicts.append(f"{field}: titel={tv} / annonsinfo={rv}")

    for field in boolean_fields:
        tv, rv = bool(title_features.get(field)), bool(raw_features.get(field))
        if tv:
            evidence.setdefault(field, []).append("title")
        if rv:
            evidence.setdefault(field, []).append("listing_text")
        merged[field] = tv or rv
        if rv and not tv:
            enriched.append(field)

    if not conflicts and raw_features:
        order = {"low": 0, "medium": 1, "high": 2}
        title_pc = str(title_features.get("player_match_confidence") or "low")
        raw_pc = str(raw_features.get("player_match_confidence") or "low")
        if order.get(raw_pc, 0) > order.get(title_pc, 0) and merged.get("player_name") == raw_features.get("player_name"):
            merged["player_match_confidence"] = raw_pc
            merged["player_match_type"] = raw_features.get("player_match_type", "listing_text")

    lot_info = detect_lot_info(f"{title} {raw_text}")
    if lot_info.get("is_lot"):
        merged["is_lot"] = True
        merged["lot_count"] = lot_info.get("lot_count")
        merged["lot_confidence"] = lot_info.get("lot_confidence", "none")

    serial = merged.get("serial_number")
    merged["is_low_serial"] = serial is not None and serial <= 50
    merged["is_mid_serial"] = serial is not None and 51 <= serial <= 199
    merged["is_high_serial"] = serial is not None and serial >= 200
    merged["is_1of1"] = serial == 1 or bool(merged.get("is_1of1"))
    merged["identity_evidence_sources"] = evidence
    merged["identity_conflicts"] = conflicts
    merged["identity_enriched_fields"] = sorted(set(enriched))
    merged.update(build_card_identity(merged))
    if conflicts:
        merged["card_identity_confidence"] = "low"
    merged["identity_confidence_score"] = compute_identity_confidence_score(merged)
    return merged

def detect_sale_type(item):
    # Prefer a structured value if the fetcher or an imported source already
    # provides one. The current Tradera fetcher normally falls back to raw_text.
    explicit = str(item.get("sale_type") or "").strip().casefold()
    if explicit in {"köp nu", "kop nu", "buy now", "buy it now"}:
        return "Köp nu"
    if explicit in {"auktion", "auction"}:
        return "Auktion"

    text = (
        item.get(
            "raw_text",
            "",
        )
        or ""
    ).lower()

    if "köp nu" in text:
        return "Köp nu"

    if (
        "utropspris" in text
        or "ledande bud" in text
        or " bud" in text
    ):
        return "Auktion"

    return "Okänd"


def compute_entry_cost(item, total_cost):
    """Return a conservative acquisition cost for ranking and profit math.

    A Buy-now price is executable at the displayed amount. An auction price is
    only the current/starting price and can rise before closing. We therefore
    add a modest auction buffer so an early low bid does not masquerade as a
    guaranteed flip margin. The original displayed total_cost is kept intact.
    """
    if total_cost is None:
        return None, 0

    if detect_sale_type(item) != "Auktion":
        return float(total_cost), 0

    price = float(item.get("pris") or 0)
    # Minimum buffer matters on cheap cards; the cap prevents the heuristic
    # from dominating expensive auctions where we lack bid-history data.
    buffer = round(max(15.0, min(price * 0.12, 75.0)), 2)
    return round(float(total_cost) + buffer, 2), buffer


def get_player_profile(
    features,
    sport,
):
    player_name = normalize_name(
        features.get(
            "player_name"
        )
    )

    database = get_player_database(
        sport
    )

    if not player_name:
        return {
            "name": None,
            "score": 15,
            "tier": "weak",
            "match_confidence": "low",
        }

    if player_name in database:
        score, tier = database[player_name]
        return {
            "name": player_name,
            "score": score,
            "tier": tier,
            "match_confidence": features.get("player_match_confidence", "high"),
        }

    # Okända parserträffar ska inte få ett artificiellt medium-score.
    # Hellre försiktig osäkerhet än falsk precision.
    score = 25
    if features.get("is_rookie"):
        score += 5

    return {
        "name": player_name,
        "score": min(score, 35),
        "tier": "weak",
        "match_confidence": features.get("player_match_confidence", "low"),
    }



def collectible_demand_factor(player_score):
    """Scale premium traits by actual player demand instead of treating them as universal value.

    Serial numbering, autos and memorabilia can make a card scarcer, but scarcity on a
    weak player does not create the same resale market as scarcity on an elite name.
    """
    score = float(player_score or 0)
    if score >= 85:
        return 1.00
    if score >= 70:
        return 0.85
    if score >= 55:
        return 0.65
    if score >= 40:
        return 0.45
    return 0.25


def premium_trait_bonus(features, player_score):
    """Return conservative title-derived premium bonus and supporting reasons.

    This is deliberately not a market valuation. It only adjusts the heuristic until
    stronger comparable-price evidence exists.
    """
    demand = collectible_demand_factor(player_score)
    bonus = 0.0
    confidence_bonus = 0.0
    reasons = []

    if features.get("is_auto"):
        bonus += 24 * demand
        confidence_bonus += 0.04 * demand
        reasons.append("autograf")

    if features.get("is_patch") or features.get("is_jersey"):
        bonus += 9 * demand
        confidence_bonus += 0.02 * demand
        reasons.append("patch/relic")

    if features.get("is_game_worn"):
        bonus += 8 * demand
        confidence_bonus += 0.015 * demand
        reasons.append("game/match worn")

    serial = features.get("serial_number")
    if features.get("is_1of1"):
        # Even a 1/1 has scarcity value, but title-only valuation is highly uncertain.
        scarcity_factor = max(0.45, demand)
        bonus += 40 * scarcity_factor
        confidence_bonus += 0.025 * demand
        reasons.append("1/1")
    elif serial is not None:
        if serial <= 10:
            raw_bonus = 30
        elif serial <= 25:
            raw_bonus = 22
        elif serial <= 50:
            raw_bonus = 15
        elif serial <= 99:
            raw_bonus = 9
        elif serial <= 199:
            raw_bonus = 4
        else:
            raw_bonus = 1
        bonus += raw_bonus * max(0.35, demand)
        reasons.append(f"numrerat /{serial}")

    return round(bonus), confidence_bonus, reasons


def parallel_trait_bonus(features, player_score):
    """Apply a cautious premium for recognized parallels and expose uncertainty.

    Parallel names are useful value signals, but they must never dominate player
    demand or a serial number. Generic colour labels receive the smallest effect.
    """
    parallel = str(features.get("parallel") or "").strip()
    if not parallel:
        return 0, 0.0, [], []

    tier = str(features.get("parallel_tier") or "standard").lower()
    match_confidence = str(features.get("parallel_confidence") or "low").lower()
    demand = collectible_demand_factor(player_score)

    raw_bonus = {
        "elite": 24,
        "rare": 15,
        "strong": 9,
        "standard": 4,
    }.get(tier, 3)

    # No colour/parallel should magically rescue a low-demand player.
    bonus = round(raw_bonus * max(0.25, demand))
    confidence_bonus = 0.0
    if match_confidence == "high":
        confidence_bonus = 0.018 * demand
    elif match_confidence == "medium":
        confidence_bonus = 0.008 * demand

    reasons = [f"parallel: {parallel}"]
    risks = []
    if match_confidence != "high":
        risks.append("parallelvariant bör verifieras mot bild/checklista")
    if float(player_score or 0) < 55:
        risks.append("parallelpremie begränsas av svag spelarmarknad")

    return bonus, confidence_bonus, reasons, risks


def rookie_trait_bonus(features, player_score, player_match_confidence="low"):
    """Conservative rookie premium tied to demand *and* rookie-program quality.

    A generic RC label is only a small positive signal. Named flagship rookie
    programs (for example Young Guns or Future Watch Auto) can add more value,
    but only when the player market is strong. This prevents "rookie" from
    becoming a universal shortcut to a high valuation.
    """
    if not features.get("is_rookie"):
        return 0, 0.0, [], []

    demand = collectible_demand_factor(player_score)
    variant = str(features.get("rookie_variant") or "Generic Rookie")
    tier = str(features.get("rookie_tier") or "standard").lower()

    base_bonus = 10
    variant_bonus = {
        "iconic": 14,
        "strong": 7,
        "standard": 0,
    }.get(tier, 0)

    # Weak/unknown names still receive only a small fraction of any rookie premium.
    demand_floor = 0.22 if tier == "standard" else 0.28
    bonus = round((base_bonus + variant_bonus) * max(demand_floor, demand))

    confidence_bonus = 0.0
    reasons = ["rookie/RC"]
    risks = []

    if variant != "Generic Rookie":
        reasons.append(f"rookieprogram: {variant}")

    specific = bool(features.get("year") or features.get("set_name") or variant != "Generic Rookie")
    if player_match_confidence in {"high", "medium"} and specific:
        confidence_bonus = (0.025 + (0.012 if tier == "iconic" else 0.006 if tier == "strong" else 0.0)) * demand
    else:
        risks.append("rookieetikett är inte fullt verifierad mot år/set")

    if float(player_score or 0) < 55:
        risks.append("rookiekort på svag spelarmarknad")
        if tier in {"iconic", "strong"}:
            risks.append("känt rookieprogram väger inte upp svag spelarefterfrågan")

    if tier == "standard" and not features.get("set_name"):
        risks.append("generisk rookieetikett utan identifierat rookieprogram")

    return bonus, confidence_bonus, reasons, risks


def grading_trait_bonus(features, player_score):
    """Value recognized grading conservatively instead of treating every slab equally."""
    grade = str(features.get("grade") or "").upper().strip()
    company = str(features.get("grading_company") or "").upper().strip()
    if not grade:
        return 0, 0.0, [], []

    match = re.search(r"(10|9\.5|9|8\.5|8|7\.5|7|6)$", grade)
    if not match:
        return 0, 0.0, ["graderat"], ["graderingsnivå kunde inte tolkas säkert"]

    numeric = float(match.group(1))
    demand = collectible_demand_factor(player_score)
    raw = 0

    if company == "PSA":
        raw = 18 if numeric >= 10 else 8 if numeric >= 9 else 2 if numeric >= 8 else 0
    elif company == "BGS":
        raw = 20 if numeric >= 10 else 14 if numeric >= 9.5 else 6 if numeric >= 9 else 1 if numeric >= 8.5 else 0
    elif company == "SGC":
        raw = 14 if numeric >= 10 else 8 if numeric >= 9.5 else 5 if numeric >= 9 else 1 if numeric >= 8 else 0
    else:
        return 0, 0.0, ["graderat"], ["okänt graderingsbolag ger inget automatiskt värdepåslag"]

    bonus = round(raw * max(0.30, demand))
    confidence_bonus = 0.015 * demand if raw > 0 else 0.0
    reasons = [f"{company} {numeric:g}"]
    risks = []

    if numeric < 9:
        risks.append("lägre grade ger begränsad premie")
    if float(player_score or 0) < 55 and raw > 0:
        risks.append("graderingspremie begränsas av svag spelarmarknad")

    return bonus, confidence_bonus, reasons, risks


def estimate_title_value(
    item,
    sport,
):
    title = item.get(
        "titel",
        "",
    )

    price = (
        item.get(
            "pris",
            0,
        )
        or 0
    )

    shipping = normalize_shipping(
        item.get("frakt")
    )

    total_cost = total_acquisition_cost(
        price,
        item.get("frakt"),
    )

    features = get_listing_features(
        item,
        sport,
    )

    profile = get_player_profile(
        features,
        sport,
    )

    set_name = features.get(
        "set_name"
    )

    sets = (
        FOOTBALL_SETS
        if sport == "football"
        else HOCKEY_SETS
    )

    set_hype = sets.get(
        set_name,
        0,
    )

    value = 8
    confidence = 0.24

    reasons = []
    risks = []

    player_match_confidence = profile.get("match_confidence", "low")
    if player_match_confidence == "medium":
        confidence -= 0.03
        reasons.append("spelarnamn identifierat med viss stavningstolerans")
    elif player_match_confidence == "low":
        confidence -= 0.10
        risks.append("osäker spelaridentifiering")

    value += round(
        profile["score"]
        * 0.22
    )

    if profile["score"] >= 85:
        confidence += 0.12

        reasons.append(
            "mycket stark "
            "spelarefterfrågan"
        )

    elif profile["score"] >= 70:
        confidence += 0.07

        reasons.append(
            "stark "
            "spelarefterfrågan"
        )

    elif profile["score"] < 40:
        confidence -= 0.05

        risks.append(
            "svag spelarmarknad"
        )

    if set_hype:
        value += set_hype
        confidence += 0.04

        reasons.append(
            f"starkt set: "
            f"{set_name}"
        )

    rookie_bonus, rookie_confidence, rookie_reasons, rookie_risks = rookie_trait_bonus(
        features,
        profile["score"],
        profile.get("match_confidence", "low"),
    )
    value += rookie_bonus
    confidence += rookie_confidence
    reasons.extend(rookie_reasons)
    risks.extend(rookie_risks)

    parallel_bonus, parallel_confidence, parallel_reasons, parallel_risks = parallel_trait_bonus(
        features,
        profile["score"],
    )
    value += parallel_bonus
    confidence += parallel_confidence
    reasons.extend(parallel_reasons)
    risks.extend(parallel_risks)

    premium_bonus, premium_confidence, premium_reasons = premium_trait_bonus(
        features,
        profile["score"],
    )
    value += premium_bonus
    confidence += premium_confidence
    reasons.extend(premium_reasons)

    serial = features.get(
        "serial_number"
    )

    if premium_reasons and profile["score"] < 55:
        risks.append(
            "premiumegenskaper har begränsad värdeeffekt på svag spelarmarknad"
        )

    grade_bonus, grade_confidence, grade_reasons, grade_risks = grading_trait_bonus(
        features,
        profile["score"],
    )
    value += grade_bonus
    confidence += grade_confidence
    reasons.extend(grade_reasons)
    risks.extend(grade_risks)

    if features.get(
        "is_lot"
    ):
        value -= 12
        confidence -= 0.10

        risks.append("samlingsannons")
        if features.get("lot_count"):
            risks.append(f"flera kort i samma annons ({features['lot_count']} st) – styckvärde ej verifierat")
        else:
            risks.append("flera kort kan ingå – styckvärde ej verifierat")

    premium_sets = (
        FOOTBALL_PREMIUM
        if sport == "football"
        else HOCKEY_PREMIUM
    )

    premium_like = (
        set_name in premium_sets
        or features.get(
            "is_auto"
        )
        or features.get(
            "is_low_serial"
        )
    )

    if (
        premium_like
        and profile["score"] < 55
    ):
        value *= 0.62
        confidence -= 0.08

        risks.append(
            "premium trap"
        )

        reasons.append(
            "premiumkort men "
            "spelaren har svag "
            "efterfrågan"
        )

    if (
        premium_like
        and profile["score"] < 70
        and total_cost >= 200
    ):
        value *= 0.82

        risks.append(
            "dyrt premiumkort "
            "på mellannamn"
        )

    if total_cost <= 30:
        value += 4

    value = max(
        0,
        round(value),
    )

    confidence = max(
        0.05,
        min(
            confidence,
            0.92,
        ),
    )

    return (
        value,
        confidence,
        reasons,
        risks,
        total_cost,
        features,
        profile,
    )




def compute_hidden_find_signal(item, features, listing_quality, market_signals=None):
    """Score listing discoverability weakness, not card value.

    A hidden-find signal may increase review priority but must never create
    market value, profit, max bid or a BUY decision on its own.
    """
    title = str(item.get("titel") or item.get("title") or "").strip()
    norm = re.sub(r"\s+", " ", title.casefold()).strip()
    raw = str(item.get("raw_text") or "")
    score = 0
    reasons = []

    # Generic/underspecified titles are easier for informed buyers to miss.
    generic_terms = ("hockeykort", "fotbollskort", "samlarkort", "kort lot", "kortlot", "kort paket", "kortpaket")
    if len(title) < 28 or any(norm == term or norm.startswith(term + " ") for term in generic_terms):
        score += 20
        reasons.append("kort eller generisk rubrik")

    if features.get("player_name") and features.get("player_match_type") not in {"exact", "alias"}:
        score += 18
        reasons.append("spelaren verkar inte vara tydligt standardskriven i rubriken")

    if features.get("player_name") and features.get("player_match_confidence") == "low":
        score += 10
        reasons.append("osäker spelartext kan minska sökbarheten")

    # Valuable identity information present in listing text but missing from title.
    enriched = set(features.get("identity_enriched_fields") or [])
    important = enriched.intersection({"set_name", "season", "card_number", "parallel", "serial_numbered", "rookie", "autograph", "patch", "grade"})
    if important:
        score += min(30, 8 + 5 * len(important))
        reasons.append("viktig kortinformation saknas i rubriken men finns i annonsinformationen")

    if features.get("is_lot"):
        score += 10
        reasons.append("lot/paket kan dölja enskilda kort")

    lq = int((listing_quality or {}).get("score", 0) or 0)
    if lq < 55:
        score += 12
        reasons.append("svagt beskriven annons")
    elif lq < 72:
        score += 6

    # Known collector signals hidden outside the title deserve manual review only.
    if market_signals and raw:
        title_signals = detect_market_knowledge_signals(title, sport=features.get("sport"))
        if len(market_signals) > len(title_signals):
            score += 10
            reasons.append("samlarsignal verkar saknas i rubriken")

    score = max(0, min(100, score))
    if score >= 55:
        label = "Dolt fynd-kandidat"
    elif score >= 35:
        label = "Möjligen dold"
    else:
        label = "Normal synlighet"
    return {"score": score, "label": label, "reasons": reasons[:5], "is_hidden_candidate": score >= 55}

def compute_market_edge(item, hidden_find, listing_quality, features, risk_analysis=None):
    """Estimate *why* this listing may be mispriced or overlooked.

    Edge is deliberately orthogonal to valuation: it can prioritize review, but
    it never creates a SEK value, profit estimate, max bid or BUY decision.
    """
    score = 0
    reasons = []
    edge_types = []

    hidden = int((hidden_find or {}).get("score", 0) or 0)
    if hidden >= 70:
        score += 28
        reasons.append("annonsen har tydliga sökbarhetsbrister")
        edge_types.append("sökbarhet")
    elif hidden >= 55:
        score += 20
        reasons.append("annonsen kan vara lätt för andra köpare att missa")
        edge_types.append("sökbarhet")
    elif hidden >= 35:
        score += 10

    seller_count = int(item.get("seller_listing_count", 0) or 0)
    seller_generic_ratio = float(item.get("seller_generic_title_ratio", 0) or 0)
    if seller_count >= 4 and seller_generic_ratio >= 0.60:
        score += 22
        reasons.append("säljaren använder ofta generiska kortrubriker")
        edge_types.append("säljarpresentation")
    elif seller_count >= 3 and seller_generic_ratio >= 0.40:
        score += 12
        reasons.append("säljarens övriga annonser är ofta svagt specificerade")
        edge_types.append("säljarpresentation")

    enriched = set(features.get("identity_enriched_fields") or [])
    if enriched.intersection({"parallel", "serial_numbered", "rookie", "autograph", "patch", "grade", "card_number"}):
        score += 18
        reasons.append("kortidentitet går att utläsa bättre än rubriken antyder")
        edge_types.append("informationsgap")

    lq = int((listing_quality or {}).get("score", 0) or 0)
    identity = int(features.get("identity_confidence_score", 0) or 0)
    # Poor presentation + strong underlying identity is a useful asymmetry.
    if lq < 60 and identity >= 70:
        score += 18
        reasons.append("svag annons men relativt stark kortidentifiering")
        edge_types.append("informationsasymmetri")

    # Edge must not masquerade as safety. High analytical risk caps it.
    risk = int((risk_analysis or {}).get("score", 0) or 0)
    if risk >= 75:
        score = min(score, 55)
        reasons.append("hög analysrisk begränsar edge-signalen")
    elif risk >= 60:
        score = min(score, 70)

    score = max(0, min(100, score))
    if score >= 70:
        label = "Stark marknadsedge"
    elif score >= 50:
        label = "Intressant edge"
    elif score >= 30:
        label = "Möjlig edge"
    else:
        label = "Ingen tydlig edge"
    return {
        "score": score,
        "label": label,
        "reasons": reasons[:5],
        "types": list(dict.fromkeys(edge_types)),
        "is_edge_candidate": score >= 50,
    }


def assess_listing_quality(item, features):
    """Assess whether the listing text supports the card identity used by FlipFynd.

    Poorly written listings can be genuine bargains, so this does not punish a
    listing merely for being short. It focuses on ambiguity that can make the
    valuation itself unsafe: missing product identity, vague wording, or a
    premium/variant claim without enough supporting identifiers.
    """
    title = str(item.get("titel") or "").strip()
    raw = str(item.get("raw_text") or "").strip()
    text = f"{title} {raw}".casefold()

    score = 100
    warnings = []
    blockers = []
    positive = []

    if features.get("player_name") and features.get("player_match_confidence") != "low":
        positive.append("spelaren är identifierad")
    else:
        score -= 35
        blockers.append("spelaren är inte säkert identifierad")

    if features.get("set_name"):
        positive.append("set/program identifierat")
    else:
        score -= 18
        warnings.append("set/program saknas eller är otydligt")

    if features.get("season") or features.get("year"):
        positive.append("år/säsong identifierad")
    else:
        score -= 10
        warnings.append("år/säsong saknas")

    if features.get("card_number"):
        positive.append("kortnummer identifierat")
    else:
        score -= 8
        warnings.append("kortnummer saknas")

    if features.get("parallel") and not features.get("set_name"):
        score -= 12
        blockers.append("variant anges men set/program är inte säkert identifierat")

    premium_claim = bool(
        features.get("is_auto")
        or features.get("is_patch")
        or features.get("grade")
        or features.get("parallel")
        or features.get("serial_number")
    )
    if premium_claim and not (features.get("set_name") and (features.get("year") or features.get("season"))):
        score -= 10
        warnings.append("premiumegenskap utan full produktidentitet")

    vague_patterns = [
        r"\bse\s+bild(?:er)?\b",
        r"\bok[aä]nd(?:t)?\b",
        r"\bvet\s+ej\b",
        r"\bos[aä]ker\b",
        r"\btror\s+(?:det|att)\b",
        r"\bdiverse\b",
    ]
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in vague_patterns):
        score -= 18
        warnings.append("annonsen använder vag/osäker beskrivning")

    meaningful_tokens = re.findall(r"[A-Za-zÅÄÖåäö0-9]+", title)
    if len(meaningful_tokens) <= 3:
        score -= 10
        warnings.append("mycket kort annonstitel")

    if not str(item.get("saljare") or "").strip():
        score -= 3
        warnings.append("säljaruppgift saknas i inläst data")

    if features.get("identity_conflicts"):
        score -= 35
        blockers.append("motstridig kortinformation mellan titel och annonsinfo")

    score = max(0, min(100, score))
    if blockers or score < 45:
        level = "låg"
    elif score < 70:
        level = "medel"
    else:
        level = "hög"

    return {
        "score": score,
        "level": level,
        "warnings": warnings,
        "blockers": blockers,
        "positive": positive,
        "clear_buy_safe": not blockers and score >= 55,
    }


def compute_deal_confidence(
    listing_quality,
    analysis_confidence,
    player_match_confidence,
    card_identity_confidence,
    comparable_count,
    comp_confidence,
    extreme_discount=False,
    is_lot=False,
):
    """Return a user-facing confidence score for whether the *deal* is trustworthy.

    This is intentionally different from sale probability or card quality. It
    answers: how much evidence does FlipFynd have that this exact listing is
    really the card/value combination the valuation assumes?
    """
    listing_score = max(0, min(100, int((listing_quality or {}).get("score", 0))))
    analysis_score = max(0, min(100, round(float(analysis_confidence or 0) * 100)))

    player_scores = {"high": 100, "medium": 70, "low": 20}
    identity_scores = {"high": 100, "medium": 72, "low": 30}
    comp_scores = {"hög": 100, "medel": 72, "låg": 42, "none": 25, "": 25}

    player_score = player_scores.get(str(player_match_confidence or "low").casefold(), 20)
    identity_score = identity_scores.get(str(card_identity_confidence or "low").casefold(), 30)
    comp_level = str(comp_confidence or "none").casefold()
    comp_score = comp_scores.get(comp_level, 35)

    # Asking-price comps are useful supporting evidence but never dominate the
    # score. Sparse comps are deliberately capped.
    if comparable_count <= 0:
        comp_score = min(comp_score, 25)
    elif comparable_count == 1:
        comp_score = min(comp_score, 40)
    elif comparable_count == 2:
        comp_score = min(comp_score, 60)
    elif comparable_count >= 5:
        comp_score = min(100, comp_score + 5)

    score = round(
        listing_score * 0.24
        + analysis_score * 0.20
        + player_score * 0.18
        + identity_score * 0.23
        + comp_score * 0.15
    )

    penalties = []
    if extreme_discount:
        score -= 18
        penalties.append("extrem prisavvikelse kräver manuell verifiering")
    if is_lot:
        score -= 30
        penalties.append("annonsen verkar innehålla flera kort")
    if (listing_quality or {}).get("blockers"):
        score = min(score, 54)
        penalties.append("kortidentiteten har blockerande osäkerhet")
    if str(player_match_confidence or "low").casefold() == "low":
        score = min(score, 44)
    if str(card_identity_confidence or "low").casefold() == "low":
        score = min(score, 49)

    score = max(0, min(100, score))
    if score >= 80:
        level = "hög"
    elif score >= 60:
        level = "medel"
    else:
        level = "låg"

    strengths = []
    if listing_score >= 70:
        strengths.append("tydlig annonsinformation")
    if player_score >= 100:
        strengths.append("säker spelaridentifiering")
    if identity_score >= 100:
        strengths.append("stark kortidentitet")
    if comparable_count >= 3 and comp_score >= 60:
        strengths.append("användbara jämförelseannonser")

    weaknesses = list(penalties)
    if comparable_count <= 1:
        weaknesses.append("få eller inga oberoende jämförelseannonser")
    if listing_score < 55:
        weaknesses.append("svag annonsinformation")
    if analysis_score < 45:
        weaknesses.append("låg analyssäkerhet")

    return {
        "score": score,
        "level": level,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "components": {
            "annons": listing_score,
            "analys": analysis_score,
            "spelare": player_score,
            "kortidentitet": identity_score,
            "comps": comp_score,
        },
    }

def compute_specificity(
    features,
    title,
):
    score = 0

    if features.get(
        "player_name"
    ):
        score += 25

    if features.get(
        "set_name"
    ):
        score += 20

    if features.get(
        "year"
    ):
        score += 8

    if (
        features.get(
            "serial_number"
        )
        is not None
    ):
        score += 12

    if features.get(
        "grade"
    ):
        score += 8

    if len(
        (
            title
            or ""
        ).split()
    ) >= 5:
        score += 8

    if features.get(
        "is_lot"
    ):
        score -= 20

    return max(
        0,
        min(
            score,
            100,
        ),
    )


def compute_liquidity(
    features,
    profile,
    total_cost,
    sport,
):
    score = (
        18
        + profile["score"]
        * 0.45
    )

    sets = (
        FOOTBALL_SETS
        if sport == "football"
        else HOCKEY_SETS
    )

    score += (
        sets.get(
            features.get(
                "set_name"
            ),
            0,
        )
        * 0.55
    )

    if features.get(
        "is_rookie"
    ):
        score += 6 * collectible_demand_factor(profile["score"])

    if features.get(
        "is_auto"
    ):
        score += 4

    if total_cost <= 150:
        score += 8

    if total_cost >= 800:
        score -= 15

    elif total_cost >= 500:
        score -= 9

    elif total_cost >= 300:
        score -= 4

    if profile["score"] < 40:
        score -= 12

    return round(
        max(
            0,
            min(
                score,
                100,
            ),
        ),
        1,
    )


def compute_liquidity_evidence(
    base_liquidity,
    profile,
    total_cost,
    comparable_details=None,
    sold_comparable_count=0,
    asking_comparable_count=0,
):
    """Refine heuristic liquidity with observable market turnover evidence.

    Sold-comps volume and recency are stronger evidence than asking inventory.
    Missing sold data is treated as uncertainty, not proof that a card is illiquid.
    """
    details = list(comparable_details or [])
    sold = [d for d in details if d.get("market_state") == "sold"]
    ages = [d.get("age_days") for d in sold if isinstance(d.get("age_days"), (int, float))]
    recent_30 = sum(1 for age in ages if age <= 30)
    recent_90 = sum(1 for age in ages if age <= 90)
    median_age = statistics.median(ages) if ages else None

    score = float(base_liquidity or 0)
    evidence = "heuristic"
    reasons = []

    if sold_comparable_count > 0:
        evidence = "sold"
        turnover_score = min(100.0, recent_30 * 22.0 + max(0, recent_90 - recent_30) * 10.0 + max(0, sold_comparable_count - recent_90) * 4.0)
        if median_age is not None:
            if median_age <= 30:
                turnover_score += 10
            elif median_age > 180:
                turnover_score -= 10
        turnover_score = max(0.0, min(100.0, turnover_score))
        # Observable sales should dominate, while player/set heuristics remain a prior.
        score = score * 0.45 + turnover_score * 0.55
        reasons.append(f"{sold_comparable_count} verifierade avslut i comp-underlaget")
        if recent_30:
            reasons.append(f"{recent_30} avslut senaste 30 dagarna")
        elif recent_90:
            reasons.append(f"{recent_90} avslut senaste 90 dagarna")
        else:
            reasons.append("inga färska avslut i comp-underlaget")
    elif asking_comparable_count > 0:
        evidence = "asking_only"
        # Active inventory is weak evidence of demand. Never let it create high liquidity.
        inventory_support = min(55.0, 18.0 + asking_comparable_count * 4.0)
        score = score * 0.80 + inventory_support * 0.20
        score = min(score, 68.0)
        reasons.append("endast aktiva annonser – omsättning ej verifierad")
    else:
        reasons.append("ingen observerad omsättningsdata – heuristisk säljbarhet")
        score = min(score, 72.0)

    if total_cost >= 800:
        score = min(score, 72.0)
    if profile.get("score", 0) < 40 and sold_comparable_count < 2:
        score = min(score, 55.0)

    score = round(max(0.0, min(100.0, score)), 1)
    if score >= 80:
        level, label = "mycket hög", "Mycket lättsålt"
    elif score >= 65:
        level, label = "hög", "Lättsålt"
    elif score >= 50:
        level, label = "normal", "Normalt"
    elif score >= 35:
        level, label = "låg", "Trögsålt"
    else:
        level, label = "mycket låg", "Svårsålt"

    return {
        "score": score,
        "level": level,
        "label": label,
        "evidence": evidence,
        "sold_30d": recent_30,
        "sold_90d": recent_90,
        "median_sold_age_days": round(median_age, 1) if median_age is not None else None,
        "reasons": reasons,
    }


def compute_risk_model(
    *,
    valuation_confidence_score,
    identity_confidence_score,
    liquidity_score,
    listing_quality_score,
    sold_comparable_count=0,
    asking_comparable_count=0,
    rejected_comparable_count=0,
    comparable_details=None,
    player_match_confidence="low",
    risks=None,
    is_lot=False,
    extreme_discount=False,
    sale_type="",
):
    """Return a transparent 0-100 purchase risk score.

    0 means well-supported/low risk and 100 means highly uncertain/high risk.
    The model is evidence-led: weak valuation/identity, missing sold comps,
    price dispersion, rejected comps and poor liquidity all increase risk.
    """
    valuation = max(0.0, min(100.0, float(valuation_confidence_score or 0)))
    identity = max(0.0, min(100.0, float(identity_confidence_score or 0)))
    liquidity = max(0.0, min(100.0, float(liquidity_score or 0)))
    listing_quality = max(0.0, min(100.0, float(listing_quality_score or 0)))
    sold_count = max(0, int(sold_comparable_count or 0))
    asking_count = max(0, int(asking_comparable_count or 0))
    rejected_count = max(0, int(rejected_comparable_count or 0))
    risk_flags = list(risks or [])

    score = 10.0
    reasons = []
    components = {}

    valuation_risk = (100.0 - valuation) * 0.28
    identity_risk = (100.0 - identity) * 0.18
    liquidity_risk = (100.0 - liquidity) * 0.14
    listing_risk = (100.0 - listing_quality) * 0.10
    score += valuation_risk + identity_risk + liquidity_risk + listing_risk
    components.update({
        "valuation": round(valuation_risk, 1),
        "identity": round(identity_risk, 1),
        "liquidity": round(liquidity_risk, 1),
        "listing_quality": round(listing_risk, 1),
    })

    if sold_count >= 4:
        score -= 12
        reasons.append(f"{sold_count} verifierade avslut minskar marknadsrisken")
    elif sold_count >= 2:
        score -= 7
        reasons.append(f"{sold_count} verifierade avslut ger visst prisstöd")
    elif sold_count == 1:
        score -= 2
        reasons.append("endast ett verifierat avslut")
    else:
        score += 10
        if asking_count:
            reasons.append("inga verifierade avslut – aktiva annonser är bara stöd")
        else:
            reasons.append("inga verifierade avslut i underlaget")

    total_considered = sold_count + asking_count + rejected_count
    if rejected_count:
        rejection_ratio = rejected_count / max(total_considered, 1)
        rejection_penalty = min(12.0, rejected_count * 1.5 + rejection_ratio * 8.0)
        score += rejection_penalty
        components["rejected_comps"] = round(rejection_penalty, 1)
        reasons.append(f"{rejected_count} comps har diskvalificerats")

    sold_prices = []
    for comp in list(comparable_details or []):
        if comp.get("market_state") != "sold":
            continue
        price = comp.get("total_price") if comp.get("total_price") not in (None, "") else comp.get("price")
        if isinstance(price, (int, float)) and price > 0:
            sold_prices.append(float(price))
    if len(sold_prices) >= 2:
        mean_price = statistics.mean(sold_prices)
        if mean_price > 0:
            dispersion = statistics.pstdev(sold_prices) / mean_price
            components["sold_price_dispersion"] = round(dispersion, 3)
            if dispersion > 0.50:
                score += 13
                reasons.append("stor prisvariation mellan verifierade avslut")
            elif dispersion > 0.30:
                score += 8
                reasons.append("tydlig prisvariation mellan verifierade avslut")
            elif dispersion > 0.15:
                score += 3

    pmc = str(player_match_confidence or "low").casefold()
    if pmc == "low":
        score += 12
        reasons.append("osäker spelaridentifiering")
    elif pmc == "medium":
        score += 5
        reasons.append("spelarnamnet är inte exakt matchat")

    if is_lot:
        score += 20
        reasons.append("lot/paket – styckvärden är inte verifierade")
    if extreme_discount:
        score += 12
        reasons.append("extrem prisavvikelse kräver manuell kontroll")
    if str(sale_type or "").casefold() == "auktion":
        score += 3
        reasons.append("auktionspriset kan stiga före avslut")

    unique_flags = {str(r).strip().casefold() for r in risk_flags if str(r).strip()}
    flag_penalty = min(10.0, len(unique_flags) * 1.25)
    score += flag_penalty
    components["explicit_flags"] = round(flag_penalty, 1)

    score = round(max(0.0, min(100.0, score)), 1)
    if score <= 30:
        level, label = "låg", "Låg"
        max_bid_factor = 0.98
    elif score <= 60:
        level, label = "medel", "Medel"
        max_bid_factor = 0.90
    else:
        level, label = "hög", "Hög"
        max_bid_factor = 0.78 if score < 80 else 0.70

    if valuation < 35 and score > 60:
        max_bid_factor = min(max_bid_factor, 0.70)

    return {
        "score": score,
        "level": level,
        "label": label,
        "max_bid_factor": round(max_bid_factor, 2),
        "reasons": reasons[:8],
        "components": components,
    }


def compute_sale_probability(
    liquidity,
    specificity,
    profile,
    comparable_count,
    risks,
    total_cost,
):
    score = (
        8
        + liquidity * 0.45
        + specificity * 0.12
        + profile["score"] * 0.18
    )

    score += min(
        comparable_count
        * 2.5,
        12,
    )

    if total_cost <= 150:
        score += 6

    elif total_cost >= 800:
        score -= 15

    elif total_cost >= 500:
        score -= 10

    elif total_cost >= 300:
        score -= 5

    if "premium trap" in risks:
        score -= 14

    if (
        "svag spelarmarknad"
        in risks
    ):
        score -= 10

    if "samlingsannons" in risks:
        score -= 8

    return round(
        max(
            5,
            min(
                score,
                95,
            ),
        ),
        1,
    )


def get_comp_info(
    item,
    all_items,
):
    if not all_items:
        return (
            None,
            0,
            None,
        )

    analysis = (
        build_market_analysis(
            item,
            all_items,
        )
    )

    if not analysis.get(
        "success"
    ):
        return (
            None,
            0,
            analysis,
        )

    count = analysis.get(
        "comparable_count",
        0,
    )

    stats = (
        analysis.get(
            "price_stats"
        )
        or {}
    )

    value = stats.get(
        "median_comparable_total_cost"
    )

    if value is None:
        value = stats.get(
            "median_comparable_price"
        )

    return (
        value,
        count,
        analysis,
    )


def compute_comp_weight(comparable_count, comp_confidence, valuation_basis="asking"):
    """Weight comps according to evidence type.

    Realised sold prices are materially stronger evidence than active asking
    prices. Active listings therefore keep the conservative legacy weights,
    while verified sold comps can carry most of the valuation when quality is
    sufficient.
    """
    if comparable_count < 2:
        return 0.0

    level = str(comp_confidence or "låg").casefold()
    basis = str(valuation_basis or "asking").casefold()

    if basis == "sold":
        if level == "hög":
            return 0.85 if comparable_count >= 4 else 0.75
        if level == "medel":
            return 0.70 if comparable_count >= 3 else 0.60
        return 0.45

    if level == "hög":
        return 0.50 if comparable_count >= 5 else 0.40
    if level == "medel":
        return 0.40 if comparable_count >= 5 else 0.30
    return 0.20 if comparable_count >= 5 else 0.15


def compute_haircut(
    confidence,
    specificity,
    comparable_count,
    risks,
):
    haircut = 0.10

    if confidence < 0.35:
        haircut += 0.18

    elif confidence < 0.55:
        haircut += 0.10

    if specificity < 35:
        haircut += 0.12

    if comparable_count <= 1:
        haircut += 0.08

    if "premium trap" in risks:
        haircut += 0.10

    if (
        "svag spelarmarknad"
        in risks
    ):
        haircut += 0.08

    if "samlingsannons" in risks:
        haircut += 0.07

    return round(
        max(
            0.05,
            min(
                haircut,
                0.55,
            ),
        ),
        2,
    )


def compute_resale_ranges(
    estimated_value,
    haircut,
    profile,
    liquidity,
):
    if profile["score"] < 40:
        demand_multiplier = 0.72

    elif profile["score"] < 60:
        demand_multiplier = 0.86

    else:
        demand_multiplier = 1.0

    expected_multiplier = max(
        0.42,
        (
            1
            - haircut
        )
        * demand_multiplier,
    )

    floor_multiplier = max(
        0.30,
        expected_multiplier
        - 0.15,
    )

    best_multiplier = max(
        expected_multiplier,
        1.0
        + max(
            (
                liquidity
                - 60
            )
            / 250,
            0,
        ),
    )

    return (
        round(
            estimated_value
            * floor_multiplier
        ),
        round(
            estimated_value
            * expected_multiplier
        ),
        round(
            estimated_value
            * best_multiplier
        ),
    )


def compute_profit(
    total_cost,
    expected_resale,
    floor_resale,
    probability,
):
    outbound_shipping = (
        18
        if expected_resale <= 200
        else 36
    )

    selling_fee = round(
        expected_resale
        * 0.08
    )

    packaging = 3

    net_profit = (
        expected_resale
        - total_cost
        - outbound_shipping
        - selling_fee
        - packaging
    )

    floor_profit = (
        floor_resale
        - total_cost
        - outbound_shipping
        - round(
            floor_resale
            * 0.08
        )
        - packaging
    )

    risk_adjusted = (
        net_profit
        * probability
        / 100
    )

    roi = (
        net_profit
        / total_cost
        if total_cost
        else 0
    )

    return {
        "net_profit_estimate":
            round(
                net_profit,
                2,
            ),

        "floor_profit_estimate":
            round(
                floor_profit,
                2,
            ),

        "risk_adjusted_profit":
            round(
                risk_adjusted,
                2,
            ),

        "roi_estimate":
            round(
                roi,
                2,
            ),
    }


def compute_card_quality(
    features,
    profile,
    sport,
    confidence,
):
    score = 10

    score += (
        profile["score"]
        * 0.18
    )

    sets = (
        FOOTBALL_SETS
        if sport == "football"
        else HOCKEY_SETS
    )

    score += sets.get(
        features.get(
            "set_name"
        ),
        0,
    )

    if features.get(
        "is_rookie"
    ):
        score += 12 * collectible_demand_factor(profile["score"])

    if features.get(
        "is_auto"
    ):
        score += 18

    if features.get(
        "is_patch"
    ):
        score += 8

    if features.get(
        "is_low_serial"
    ):
        score += 12

    elif features.get(
        "is_mid_serial"
    ):
        score += 4

    score += (
        confidence
        * 8
    )

    return round(
        max(
            0,
            min(
                score,
                100,
            ),
        ),
        2,
    )


def compute_flip_scores(
    profits,
    probability,
    liquidity,
    quality,
    profile,
    total_cost,
    risks,
):
    if total_cost <= 100:
        affordability = 18

    elif total_cost <= 250:
        affordability = 10

    else:
        affordability = 0

    profit_signal = min(max(profits["risk_adjusted_profit"], -50), 140)
    roi_signal = min(max(profits.get("roi_estimate", 0) * 100, -50), 180)

    quick = (
        profit_signal * 0.72
        + roi_signal * 0.18
        + probability * 0.42
        + liquidity * 0.30
        + profile["score"] * 0.25
        + affordability
    )

    premium = (
        profit_signal * 0.62
        + roi_signal * 0.10
        + quality * 0.34
        + probability * 0.24
        + liquidity * 0.20
        + profile["score"] * 0.22
    )

    if "premium trap" in risks:
        quick -= 22
        premium -= 30

    if profile["score"] < 40:
        quick -= 18
        premium -= 22

    return (
        round(
            quick,
            2,
        ),
        round(
            premium,
            2,
        ),
    )



def compute_deal_score_100(
    profits,
    expected_resale,
    total_cost,
    probability,
    liquidity,
    valuation_confidence_score,
    identity_confidence_score,
    deal_confidence_score,
    risks=None,
    decision="SKIP",
    risk_score=None,
):
    """Practical 0-100 flip opportunity score.

    The score measures purchase attractiveness, not card prestige. It is capped
    when evidence is weak so uncertain listings cannot look like elite finds.
    """
    risks = list(risks or [])
    cost = max(float(total_cost or 0), 0.0)
    value = max(float(expected_resale or 0), 0.0)
    net = float((profits or {}).get("net_profit_estimate", 0) or 0)
    roi_pct = float((profits or {}).get("roi_estimate", 0) or 0) * 100.0

    discount_pct = ((value - cost) / value * 100.0) if value > 0 else 0.0
    discount_score = max(0.0, min(100.0, discount_pct / 70.0 * 100.0))
    profit_score = max(0.0, min(100.0, net / 150.0 * 100.0))
    roi_score = max(0.0, min(100.0, roi_pct / 180.0 * 100.0))
    sale_score = max(0.0, min(100.0, float(probability or 0)))
    liquidity_score = max(0.0, min(100.0, float(liquidity or 0)))
    valuation_score = max(0.0, min(100.0, float(valuation_confidence_score or 0)))
    identity_score = max(0.0, min(100.0, float(identity_confidence_score or 0)))
    evidence_score = max(0.0, min(100.0, float(deal_confidence_score or 0)))

    raw = (
        discount_score * 0.18
        + profit_score * 0.22
        + roi_score * 0.16
        + sale_score * 0.14
        + liquidity_score * 0.10
        + valuation_score * 0.10
        + identity_score * 0.05
        + evidence_score * 0.05
    )

    # Risk must hurt the opportunity, but duplicate warning text must not make
    # the score collapse unpredictably.
    if risk_score is None:
        risk_penalty = min(18.0, len(set(str(r) for r in risks)) * 2.5)
        normalized_risk = None
    else:
        normalized_risk = max(0.0, min(100.0, float(risk_score or 0)))
        risk_penalty = min(22.0, normalized_risk * 0.16 + len(set(str(r) for r in risks)) * 0.75)
    score = raw - risk_penalty

    # Evidence caps prevent false precision and spectacular scores on guesses.
    if valuation_score < 25:
        score = min(score, 64)
    elif valuation_score < 45:
        score = min(score, 74)
    if identity_score < 50 or evidence_score < 50:
        score = min(score, 69)
    if net <= 0 or roi_pct <= 0:
        score = min(score, 45)
    if decision == "SKIP":
        score = min(score, 49)
    elif decision == "KANSKE":
        score = min(score, 69)

    score = max(0, min(100, round(score)))
    if score >= 90:
        label = "Exceptionellt fynd"
    elif score >= 80:
        label = "Mycket bra fynd"
    elif score >= 70:
        label = "Bra fynd"
    elif score >= 60:
        label = "Intressant"
    elif score >= 50:
        label = "Svagt köpläge"
    else:
        label = "Pass"

    return {
        "score": score,
        "label": label,
        "components": {
            "discount": round(discount_score),
            "net_profit": round(profit_score),
            "roi": round(roi_score),
            "sale_probability": round(sale_score),
            "liquidity": round(liquidity_score),
            "valuation_confidence": round(valuation_score),
            "identity_confidence": round(identity_score),
            "evidence_confidence": round(evidence_score),
            "risk_safety": round(100.0 - normalized_risk) if normalized_risk is not None else None,
        },
    }

def compute_rank(
    raw_score,
    quick,
    premium,
    quality,
    player_score,
    strategy_mode,
):
    if strategy_mode == "premium_flip":
        score = (
            premium * 0.55
            + quick * 0.15
            + quality * 0.10
            + player_score * 0.20
        )

    elif strategy_mode == "kort":
        score = (
            quality * 0.40
            + premium * 0.20
            + quick * 0.15
            + player_score * 0.25
        )

    else:
        score = (
            quick * 0.55
            + premium * 0.10
            + quality * 0.08
            + player_score * 0.27
        )

    score += (
        raw_score
        or 0
    ) * 0.02

    return round(
        score,
        2,
    )


def compute_ranking_confidence(
    listing_quality,
    analysis_confidence,
    player_match_confidence,
    card_identity_confidence,
    deal_confidence_score=None,
):
    """Confidence used specifically when ordering opportunities.

    Full analyses can use the complete Fyndsäkerhet score, including comps.
    Fast analyses deliberately use only evidence available before comp analysis,
    so they are not unfairly punished merely because comps have not been loaded yet.
    """
    if deal_confidence_score is not None:
        return max(0, min(100, round(float(deal_confidence_score))))

    listing_score = max(0, min(100, int((listing_quality or {}).get("score", 0))))
    analysis_score = max(0, min(100, round(float(analysis_confidence or 0) * 100)))
    player_scores = {"high": 100, "medium": 70, "low": 20}
    identity_scores = {"high": 100, "medium": 72, "low": 30}
    player_score = player_scores.get(str(player_match_confidence or "low").casefold(), 20)
    identity_score = identity_scores.get(str(card_identity_confidence or "low").casefold(), 30)

    return max(
        0,
        min(
            100,
            round(
                listing_score * 0.30
                + analysis_score * 0.25
                + player_score * 0.20
                + identity_score * 0.25
            ),
        ),
    )


def adjust_rank_for_confidence(base_rank, ranking_confidence):
    """Penalise uncertain theoretical upside without hiding real bargains.

    The confidence multiplier ranges from 0.55 to 1.00. This is strong enough
    for a slightly less profitable but well-supported deal to outrank a highly
    speculative one. Negative ranks are pushed further down rather than being
    accidentally improved by multiplication.
    """
    base = float(base_rank or 0)
    confidence = max(0, min(100, float(ranking_confidence or 0)))
    factor = 0.55 + 0.45 * (confidence / 100.0)

    adjusted = base * factor if base >= 0 else base / max(factor, 0.01)
    return round(adjusted, 2)



def explain_rank_advantage(first, second):
    """Explain in plain Swedish why one ranked opportunity sits above another.

    The explanation follows the actual ranking inputs and avoids claiming that a
    higher nominal profit alone makes a deal better. It is intended for the UI
    comparison between adjacent top results.
    """
    if not first or not second:
        return []

    def num(item, key):
        try:
            return float(item.get(key, 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    messages = []
    rank_delta = num(first, "rank_score") - num(second, "rank_score")
    confidence_delta = num(first, "ranking_confidence_score") - num(second, "ranking_confidence_score")
    profit_delta = num(first, "risk_adjusted_profit") - num(second, "risk_adjusted_profit")
    sale_delta = num(first, "sale_probability") - num(second, "sale_probability")
    player_delta = num(first, "player_market_score") - num(second, "player_market_score")

    if confidence_delta >= 8:
        messages.append(
            f"Säkrare fyndunderlag (+{confidence_delta:.0f} poäng i rankingsäkerhet)."
        )
    elif confidence_delta <= -8:
        messages.append(
            f"#2 har högre fyndsäkerhet ({abs(confidence_delta):.0f} poäng), men #1 väger upp det på andra faktorer."
        )

    if profit_delta >= 20:
        messages.append(f"Högre riskjusterad vinst (+{profit_delta:.0f} kr).")
    elif profit_delta <= -20:
        messages.append(
            f"#2 har {abs(profit_delta):.0f} kr högre riskjusterad vinst, men den räcker inte för att väga upp övriga faktorer."
        )

    if sale_delta >= 8:
        messages.append(f"Högre beräknad säljchans (+{sale_delta:.0f} procentenheter).")
    elif sale_delta <= -8:
        messages.append(
            f"#2 har högre säljchans (+{abs(sale_delta):.0f} procentenheter), men #1 rankas ändå högre totalt."
        )

    if player_delta >= 10:
        messages.append(f"Starkare spelarefterfrågan (+{player_delta:.0f} poäng).")
    elif player_delta <= -10:
        messages.append(
            f"#2 har starkare spelarefterfrågan (+{abs(player_delta):.0f} poäng), men #1 vinner helhetsrankningen."
        )

    if not messages:
        messages.append(
            "Skillnaden är liten och kommer från den sammanvägda kombinationen av marginal, efterfrågan och säkerhet."
        )

    if rank_delta > 0:
        messages.insert(0, f"#1 ligger {rank_delta:.1f} rankpoäng före #2.")

    return messages[:4]

def make_decision(
    net_profit,
    risk_adjusted,
    probability,
    player_score,
    confidence=0.0,
    player_match_confidence="low",
    floor_profit=0.0,
    roi=0.0,
    total_cost=0.0,
):
    """Turn analysis into a conservative buy/watch/skip decision.

    A flip should not become a clear buy merely because the optimistic expected
    profit is large. The decision also needs reasonable capital efficiency and
    a tolerable downside in the conservative resale case.
    """
    if confidence < 0.28 or player_match_confidence == "low":
        return "SKIP"

    if (
        player_score < 35
        and net_profit < 100
    ):
        return "SKIP"

    capital = max(float(total_cost or 0), 1.0)
    downside_ratio = float(floor_profit or 0) / capital

    # A very poor floor case is not a buy, even if the expected case looks good.
    if downside_ratio < -0.40:
        if risk_adjusted >= 8 and probability >= 40 and net_profit >= 10:
            return "KANSKE"
        return "SKIP"

    if (
        risk_adjusted >= 60
        and probability >= 65
        and net_profit >= 80
        and roi >= 0.35
        and downside_ratio >= -0.15
    ):
        return "KÖP (starkt fynd)"

    if (
        risk_adjusted >= 20
        and probability >= 55
        and net_profit >= 30
        and roi >= 0.18
        and downside_ratio >= -0.25
    ):
        return "KÖP"

    if (
        risk_adjusted >= 8
        and probability >= 40
        and net_profit >= 10
        and roi >= 0.08
    ):
        return "KANSKE"

    return "SKIP"


def compute_max_purchase_price(
    item,
    expected_resale,
    floor_resale,
    probability,
    player_score,
    confidence,
    player_match_confidence,
    risk_ceiling_factor=1.0,
):
    """Return a conservative ceiling price that still qualifies as KÖP.

    The ceiling uses the same profit and decision rules as the normal analysis.
    For auctions we also apply the auction buffer at every candidate price so the
    suggested bid ceiling does not silently ignore bidding risk.
    """
    if confidence < 0.28 or player_match_confidence == "low":
        return None

    shipping = normalize_shipping(item.get("frakt"))
    sale_type = detect_sale_type(item)
    risk_ceiling_factor = max(0.50, min(1.0, float(risk_ceiling_factor or 1.0)))
    risk_adjusted_expected = float(expected_resale or 0) * risk_ceiling_factor
    risk_adjusted_floor = float(floor_resale or 0) * risk_ceiling_factor

    def qualifies(displayed_total):
        analysis_cost, _ = compute_entry_cost(
            {**item, "sale_type": sale_type},
            displayed_total,
        )
        profits = compute_profit(
            analysis_cost,
            risk_adjusted_expected,
            risk_adjusted_floor,
            probability,
        )
        decision = make_decision(
            profits["net_profit_estimate"],
            profits["risk_adjusted_profit"],
            probability,
            player_score,
            confidence=confidence,
            player_match_confidence=player_match_confidence,
            floor_profit=profits["floor_profit_estimate"],
            roi=profits["roi_estimate"],
            total_cost=analysis_cost,
        )
        return decision in {"KÖP", "KÖP (starkt fynd)"}

    # There is no useful ceiling if even a near-zero card price cannot pass.
    low = max(float(shipping), 1.0)
    if not qualifies(low):
        return None

    # No rational flip ceiling should need to exceed the expected resale value.
    high = max(float(risk_adjusted_expected), low)
    if qualifies(high):
        ceiling_total = high
    else:
        for _ in range(28):
            mid = (low + high) / 2
            if qualifies(mid):
                low = mid
            else:
                high = mid
        ceiling_total = low

    ceiling_total = max(0.0, round(ceiling_total, 2))
    max_item_price = max(0.0, round(ceiling_total - shipping, 2))

    return {
        "max_total_price": ceiling_total,
        "max_item_price": max_item_price,
        "assumed_shipping": round(shipping, 2),
        "sale_type": sale_type,
        "risk_ceiling_factor": round(risk_ceiling_factor, 2),
    }


def build_auction_bid_strategy(item, max_purchase):
    """Explain how much room remains before an auction reaches FlipFynd's bid ceiling."""
    if detect_sale_type(item) != "Auktion" or not max_purchase:
        return None

    try:
        current_item_price = float(item.get("pris") or 0)
    except (TypeError, ValueError):
        return None
    if current_item_price <= 0:
        return None

    shipping = float(max_purchase.get("assumed_shipping") or normalize_shipping(item.get("frakt")))
    max_item_price = float(max_purchase.get("max_item_price") or 0)
    max_total_price = float(max_purchase.get("max_total_price") or 0)
    current_total = current_item_price + shipping
    margin = max_item_price - current_item_price

    if margin <= 0:
        status = "STOPP"
        message = "Nuvarande bud är vid eller över FlipFynds beräknade budtak."
    else:
        share_left = margin / max(max_item_price, 1.0)
        if margin <= 10 or share_left <= 0.10:
            status = "NÄRA BUDTAK"
            message = "Mycket liten marginal återstår. Undvik att jaga auktionen över budtaket."
        elif share_left <= 0.35:
            status = "BEVAKA"
            message = "Det finns viss budmarginal kvar, men auktionen börjar närma sig taket."
        else:
            status = "AVVAKTA"
            message = "God marginal till budtaket. Det finns ingen anledning att bjuda upp priset i förtid."

    return {
        "status": status,
        "message": message,
        "current_item_price": round(current_item_price, 2),
        "current_total_price": round(current_total, 2),
        "max_item_price": round(max_item_price, 2),
        "max_total_price": round(max_total_price, 2),
        "remaining_bid_margin": round(max(0.0, margin), 2),
        "shipping": round(shipping, 2),
    }


def build_decision_diagnostics(
    decision,
    net_profit,
    risk_adjusted,
    probability,
    player_score,
    confidence,
    player_match_confidence,
    floor_profit,
    roi,
    total_cost,
):
    """Explain the most relevant gaps to the normal KÖP threshold."""
    if decision in {"KÖP", "KÖP (starkt fynd)"}:
        return []

    diagnostics = []
    capital = max(float(total_cost or 0), 1.0)
    downside_ratio = float(floor_profit or 0) / capital

    if confidence < 0.28:
        diagnostics.append(f"Analyssäkerhet {confidence:.0%}; minst 28 % krävs för ett köpbeslut.")
    if player_match_confidence == "low":
        diagnostics.append("Spelaren är inte identifierad tillräckligt säkert för ett köpbeslut.")
    if player_score < 35 and net_profit < 100:
        diagnostics.append(f"Spelarefterfrågan är låg ({player_score}/100) och vinsten kompenserar inte risken.")
    if downside_ratio < -0.25:
        diagnostics.append(f"Konservativt scenario motsvarar {downside_ratio:.0%} av inköpskostnaden; KÖP kräver minst -25 %.")
    if risk_adjusted < 20:
        diagnostics.append(f"Riskjusterad vinst {risk_adjusted:.0f} kr; KÖP kräver minst 20 kr.")
    if probability < 55:
        diagnostics.append(f"Säljchans {probability:.0f} %; KÖP kräver minst 55 %.")
    if net_profit < 30:
        diagnostics.append(f"Förväntad nettovinst {net_profit:.0f} kr; KÖP kräver minst 30 kr.")
    if roi < 0.18:
        diagnostics.append(f"Förväntad ROI {roi:.0%}; KÖP kräver minst 18 %.")

    # Keep the UI focused on the blockers that matter most.
    return diagnostics[:5]


def compute_exit_speed(
    liquidity,
    probability,
    total_cost,
):
    score = (
        liquidity * 0.6
        + probability * 0.4
    )

    if total_cost <= 150:
        score += 6

    if total_cost >= 800:
        score -= 10

    elif total_cost >= 500:
        score -= 5

    if score >= 75:
        return "Snabb"

    if score >= 55:
        return "Medel"

    return "Trög"


def build_invalid_result(
    item,
    sport,
    reason,
):
    return {
        "titel":
            item.get(
                "titel",
                "",
            ),

        "pris":
            item.get(
                "pris",
                0,
            )
            or 0,

        "frakt":
            item.get(
                "frakt"
            ),

        "total_cost":
            total_acquisition_cost(
                item.get("pris"),
                item.get("frakt"),
            )
            or 0,

        "player_name": None,
        "player_market_score": 0,
        "demand_tier": "weak",
        "player_match_confidence": "low",
        "player_match_type": "none",
        "sport": sport,

        "score":
            item.get(
                "score",
                0,
            )
            or 0,

        "uppskattat_varde": 0,
        "heuristic_estimated_value": 0,
        "comp_estimated_value": None,
        "value_source": "invalid",
        "marginal": 0,
        "confidence": 0.05,
        "rank_score": 0,
        "card_quality_score": 0,
        "hype_score": 0,
        "specificity_score": 0,
        "listing_weakness_score": 0,
        "mislist_potential": 0,
        "liquidity_score": 0,
        "sale_probability": 0,
        "uncertainty_haircut": 0.5,
        "floor_resale": 0,
        "expected_resale": 0,
        "best_case_resale": 0,
        "net_profit_estimate": 0,
        "floor_profit_estimate": 0,
        "risk_adjusted_profit": 0,
        "quick_flip_score": 0,
        "premium_flip_score": 0,
        "exit_speed": "Trög",
        "roi_estimate": 0,
        "beslut": "SKIP",
        "kommentar": reason,

        "lank":
            item.get(
                "lank",
                "",
            ),

        "raw_text": item.get("raw_text", ""),

        "sale_type":
            detect_sale_type(
                item
            ),

        "reasons": [
            reason
        ],

        "risk_flags": [
            reason
        ],

        "market_analysis_summary":
            None,

        "comparable_count": 0,

        "saljare":
            item.get(
                "saljare"
            ),

        "source_category":
            item.get(
                "source_category"
            ),

        "detail_priority_score": item.get("detail_priority_score"),
        "detail_priority_reasons": item.get("detail_priority_reasons", []),
        "detail_enrichment_status": item.get("detail_enrichment_status"),
        "detail_source": item.get("detail_source"),
        "detail_enriched_at": item.get("detail_enriched_at"),
        "detail_title": item.get("detail_title"),
        "full_description": item.get("full_description"),
        "detail_image_urls": item.get("detail_image_urls", []),
        "exact_end_text": item.get("exact_end_text"),
        "bid_count": item.get("bid_count"),
        "seller_detail": item.get("seller_detail"),
    }


def analyze_core(
    item,
    sport,
    strategy_mode,
    all_items=None,
    full=False,
):
    item = dict(item or {})
    detail_images = list(item.get("detail_image_urls") or [])
    if detail_images:
        item["image_urls"] = list(dict.fromkeys(list(item.get("image_urls") or []) + detail_images))[:16]

    title = item.get(
        "titel",
        "",
    )

    price = item.get(
        "pris"
    )

    if (
        not isinstance(
            price,
            (
                int,
                float,
            ),
        )
        or price <= 0
    ):
        return build_invalid_result(
            item,
            sport,
            "pris saknas eller är felaktigt",
        )

    (
        heuristic,
        confidence,
        reasons,
        risks,
        total_cost,
        features,
        profile,
    ) = estimate_title_value(
        item,
        sport,
    )
    # Keep sport context available to downstream discovery-only knowledge checks.
    features["sport"] = sport

    detail_evidence_fusion = build_detail_evidence_fusion(item)

    analysis_total_cost, auction_buffer = compute_entry_cost(
        item,
        total_cost,
    )
    sale_type = detect_sale_type(item)
    if sale_type == "Auktion" and auction_buffer > 0:
        risks.append("auktionspris kan stiga före avslut")
        reasons.append(
            f"auktion: {auction_buffer:.0f} kr säkerhetsmarginal används i fyndkalkylen"
        )

    specificity = (
        compute_specificity(
            features,
            title,
        )
    )

    listing_quality = assess_listing_quality(item, features)
    if features.get("identity_conflicts"):
        risks.append("motstridig kortinformation – manuell kontroll rekommenderas")
    if features.get("identity_enriched_fields"):
        reasons.append("kortidentitet kompletterad från annonsinformationen")
    if listing_quality["level"] == "låg":
        confidence = max(0.05, confidence - 0.08)
        specificity = max(0, specificity - 12)
    elif listing_quality["level"] == "medel":
        confidence = max(0.05, confidence - 0.03)

    for warning in listing_quality["warnings"]:
        risks.append(f"annonskvalitet: {warning}")
    for blocker in listing_quality["blockers"]:
        risks.append(f"identitetsrisk: {blocker}")

    liquidity = (
        compute_liquidity(
            features,
            profile,
            analysis_total_cost,
            sport,
        )
    )

    comp_value = None
    comparable_count = 0
    market_summary = None
    comp_confidence = "none"
    comp_valuation_basis = "none"
    sold_comparable_count = 0
    asking_comparable_count = 0
    comparable_details = []
    comp_valuation_range = None
    rejected_comparable_count = 0
    rejected_comparables = []
    valuation_confidence_score = 10
    valuation_confidence_level = "mycket låg"
    valuation_confidence_reasons = ["inga användbara marknadscomps"]
    valuation_confidence_components = {}

    estimated_value = heuristic
    value_source = "heuristic_only"

    # Lokal comp-analys används för båda sporterna. Anroparen ska skicka
    # sportfiltrerad data så hockey- och fotbollsannonser aldrig blandas.
    if (
        full
        and all_items
        and sport in {"hockey", "football"}
    ):
        (
            comp_value,
            comparable_count,
            market,
        ) = get_comp_info(
            item,
            all_items,
        )

        if (
            market
            and market.get(
                "success"
            )
        ):
            market_summary = market.get("summary")
            comp_valuation_basis = market.get("valuation_basis", "none")
            sold_comparable_count = int(market.get("sold_comparable_count", 0) or 0)
            asking_comparable_count = int(market.get("asking_comparable_count", 0) or 0)
            comparable_details = list(market.get("comparable_details", []) or [])
            comp_valuation_range = market.get("valuation_range")
            rejected_comparable_count = int(market.get("rejected_comparable_count", 0) or 0)
            rejected_comparables = list(market.get("rejected_comparables", []) or [])
            comp_confidence = market.get("confidence", "låg")
            valuation_confidence_score = int(market.get("valuation_confidence_score", 10) or 10)
            valuation_confidence_level = market.get("valuation_confidence_level", "mycket låg")
            valuation_confidence_reasons = list(market.get("valuation_confidence_reasons", []) or [])
            valuation_confidence_components = dict(market.get("valuation_confidence_components", {}) or {})

        if (
            comp_value
            is not None
            and comparable_count >= 2
        ):
            basis_count = sold_comparable_count if comp_valuation_basis == "sold" else asking_comparable_count
            comp_weight = compute_comp_weight(basis_count or comparable_count, comp_confidence, comp_valuation_basis)

            estimated_value = round(
                heuristic
                * (
                    1
                    - comp_weight
                )
                + comp_value
                * comp_weight
            )

            if comp_valuation_basis == "sold":
                value_source = "blended_sold_comps"
                confidence = min(
                    0.95,
                    confidence + (0.12 if comp_confidence == "hög" else 0.08 if comp_confidence == "medel" else 0.03),
                )
                reasons.append(
                    f"{sold_comparable_count} verifierade sålda comps "
                    f"({comp_confidence} comp-kvalitet); aktiva annonser väger inte som försäljningar"
                )
            else:
                value_source = "blended_current_listings"
                # Aktiva annonser är utrops-/köp nu-priser, inte bekräftade avslut.
                # Bara medel/hög comp-kvalitet får därför höja analysens confidence.
                if str(comp_confidence).casefold() in {"medel", "hög"}:
                    confidence = min(
                        0.92,
                        confidence + (0.08 if comp_confidence == "hög" and asking_comparable_count >= 5 else 0.04),
                    )
                reasons.append(
                    f"{asking_comparable_count or comparable_count} aktiva jämförelseannonser "
                    f"({comp_confidence} comp-kvalitet; begärda priser, inte sålda)"
                )

    # Värderingssäkerhet är separat från allmän analys-confidence. Om en comp-baserad
    # värdering har svagt prisunderlag får den inte samtidigt bära hög total säkerhet.
    if comp_valuation_basis != "none":
        if valuation_confidence_score < 40:
            confidence = min(confidence, 0.58)
            risks.append("låg värderingssäkerhet – prisunderlaget är svagt")
        elif valuation_confidence_score < 60:
            confidence = min(confidence, 0.72)

    liquidity_analysis = compute_liquidity_evidence(
        liquidity,
        profile,
        analysis_total_cost,
        comparable_details=comparable_details,
        sold_comparable_count=sold_comparable_count,
        asking_comparable_count=asking_comparable_count,
    )
    liquidity = liquidity_analysis["score"]

    probability = (
        compute_sale_probability(
            liquidity,
            specificity,
            profile,
            comparable_count,
            risks,
            analysis_total_cost,
        )
    )

    haircut = compute_haircut(
        confidence,
        specificity,
        comparable_count,
        risks,
    )

    (
        floor_resale,
        expected_resale,
        best_case_resale,
    ) = compute_resale_ranges(
        estimated_value,
        haircut,
        profile,
        liquidity,
    )

    profits = compute_profit(
        analysis_total_cost,
        expected_resale,
        floor_resale,
        probability,
    )

    quality = compute_card_quality(
        features,
        profile,
        sport,
        confidence,
    )

    (
        quick_score,
        premium_score,
    ) = compute_flip_scores(
        profits,
        probability,
        liquidity,
        quality,
        profile,
        analysis_total_cost,
        risks,
    )

    decision = make_decision(
        profits["net_profit_estimate"],
        profits["risk_adjusted_profit"],
        probability,
        profile["score"],
        confidence=confidence,
        player_match_confidence=profile.get("match_confidence", "low"),
        floor_profit=profits["floor_profit_estimate"],
        roi=profits["roi_estimate"],
        total_cost=analysis_total_cost,
    )

    # The current valuation model estimates one card. A multi-card listing must
    # therefore never surface as a clear buy from a misleading lot price.
    if features.get("is_lot") and decision in {"KÖP", "KÖP (starkt fynd)"}:
        decision = "KANSKE"

    # A badly described listing can still be interesting, but FlipFynd should
    # not issue a clear buy when the identity behind the valuation is ambiguous.
    if not listing_quality["clear_buy_safe"] and decision in {"KÖP", "KÖP (starkt fynd)"}:
        decision = "KANSKE"

    extreme_discount = False
    if expected_resale > 0 and analysis_total_cost > 0:
        extreme_discount = analysis_total_cost <= expected_resale * 0.12 and expected_resale >= 150
        if extreme_discount:
            risks.append("extrem prisavvikelse – verifiera att annonsen avser exakt samma kort")
            if listing_quality["level"] != "hög" and decision in {"KÖP", "KÖP (starkt fynd)"}:
                decision = "KANSKE"

    deal_confidence = compute_deal_confidence(
        listing_quality=listing_quality,
        analysis_confidence=confidence,
        player_match_confidence=profile.get("match_confidence", "low"),
        card_identity_confidence=features.get("card_identity_confidence", "low"),
        comparable_count=comparable_count,
        comp_confidence=comp_confidence,
        extreme_discount=extreme_discount,
        is_lot=bool(features.get("is_lot")),
    )

    risk_analysis = compute_risk_model(
        valuation_confidence_score=valuation_confidence_score,
        identity_confidence_score=features.get("identity_confidence_score", 0),
        liquidity_score=liquidity,
        listing_quality_score=listing_quality.get("score", 0),
        sold_comparable_count=sold_comparable_count,
        asking_comparable_count=asking_comparable_count,
        rejected_comparable_count=rejected_comparable_count,
        comparable_details=comparable_details,
        player_match_confidence=profile.get("match_confidence", "low"),
        risks=risks,
        is_lot=bool(features.get("is_lot")),
        extreme_discount=extreme_discount,
        sale_type=sale_type,
    )

    # High risk must visibly constrain recommendations, not only add warning text.
    if risk_analysis["score"] >= 75 and decision in {"KÖP", "KÖP (starkt fynd)"}:
        decision = "KANSKE"
    elif risk_analysis["score"] > 60 and decision == "KÖP (starkt fynd)":
        decision = "KÖP"

    deal_score = compute_deal_score_100(
        profits=profits,
        expected_resale=expected_resale,
        total_cost=analysis_total_cost,
        probability=probability,
        liquidity=liquidity,
        valuation_confidence_score=valuation_confidence_score,
        identity_confidence_score=features.get("identity_confidence_score", 0),
        deal_confidence_score=deal_confidence["score"],
        risks=risks,
        decision=decision,
        risk_score=risk_analysis["score"],
    )

    base_rank = compute_rank(
        item.get("score", 0) or 0,
        quick_score,
        premium_score,
        quality,
        profile["score"],
        strategy_mode,
    )
    ranking_confidence = compute_ranking_confidence(
        listing_quality=listing_quality,
        analysis_confidence=confidence,
        player_match_confidence=profile.get("match_confidence", "low"),
        card_identity_confidence=features.get("card_identity_confidence", "low"),
        deal_confidence_score=(deal_confidence["score"] if full else None),
    )
    rank = adjust_rank_for_confidence(base_rank, ranking_confidence)

    decision_diagnostics = build_decision_diagnostics(
        decision,
        profits["net_profit_estimate"],
        profits["risk_adjusted_profit"],
        probability,
        profile["score"],
        confidence,
        profile.get("match_confidence", "low"),
        profits["floor_profit_estimate"],
        profits["roi_estimate"],
        analysis_total_cost,
    )

    max_purchase = None if (features.get("is_lot") or not listing_quality["clear_buy_safe"]) else compute_max_purchase_price(
        item,
        expected_resale,
        floor_resale,
        probability,
        profile["score"],
        confidence,
        profile.get("match_confidence", "low"),
        risk_ceiling_factor=risk_analysis["max_bid_factor"],
    )
    auction_strategy = build_auction_bid_strategy(item, max_purchase)


    market_knowledge_signals = detect_market_knowledge_signals(
        f"{title} {item.get('raw_text', '') or ''}",
        sport=sport,
    )
    card_intelligence = build_card_intelligence(market_knowledge_signals, features)
    card_knowledge_library = explain_library_match(market_knowledge_signals)
    variant_hierarchy = build_variant_hierarchy(market_knowledge_signals, features)
    collector_intelligence = build_collector_intelligence_matrix(
        player_name=profile.get("name"),
        player_market_score=profile.get("score", 0),
        demand_tier=profile.get("tier"),
        card_intelligence=card_intelligence,
        features=features,
    )
    chase_knowledge_graph = build_chase_knowledge_graph(
        signals=market_knowledge_signals,
        player_name=profile.get("name"),
        player_market_score=profile.get("score", 0),
        features=features,
    )
    player_card_demand = build_player_card_demand(
        player_name=profile.get("name"),
        player_market_score=profile.get("score", 0),
        demand_tier=profile.get("tier"),
        variant_rung=variant_hierarchy.get("variant_rung", 0),
        rookie_rung=variant_hierarchy.get("rookie_rung", 0),
        chase_priority_score=chase_knowledge_graph.get("priority_score", 0),
        sold_comparable_count=sold_comparable_count,
        asking_comparable_count=asking_comparable_count,
        liquidity_score=liquidity,
        sold_30d=liquidity_analysis.get("sold_30d", 0),
        sold_90d=liquidity_analysis.get("sold_90d", 0),
        identity_confidence_score=features.get("identity_confidence_score", 0),
        valuation_confidence_score=valuation_confidence_score,
    )
    valuable_card_knowledge = build_valuable_card_knowledge(
        signals=market_knowledge_signals,
        player_name=profile.get("name"),
        player_market_score=profile.get("score", 0),
        variant_rung=variant_hierarchy.get("variant_rung", 0),
        rookie_rung=variant_hierarchy.get("rookie_rung", 0),
        sold_comparable_count=sold_comparable_count,
        valuation_confidence_score=valuation_confidence_score,
        identity_confidence_score=features.get("identity_confidence_score", 0),
        risk_score=risk_analysis.get("score", 0),
    )
    rookie_importance = build_player_rookie_importance(
        signals=market_knowledge_signals,
        features=features,
        sport=sport,
        player_name=profile.get("name"),
        player_market_score=profile.get("score", 0),
        sold_comparable_count=sold_comparable_count,
        identity_confidence_score=features.get("identity_confidence_score", 0),
        valuation_confidence_score=valuation_confidence_score,
    )
    hidden_find = compute_hidden_find_signal(
        item, features, listing_quality, market_knowledge_signals
    )
    mispriced_rookie = build_mispriced_rookie_signal(
        item=item,
        features=features,
        rookie_importance=rookie_importance,
        listing_quality=listing_quality,
        hidden_find=hidden_find,
        player_market_score=profile.get("score", 0),
        valuation_confidence_score=valuation_confidence_score,
        sold_comparable_count=sold_comparable_count,
        total_cost=total_cost,
        expected_resale=expected_resale,
        evidence_fusion=detail_evidence_fusion,
    )
    misclassified_card = build_misclassified_card_signal(
        item=item,
        features=features,
        knowledge_signals=market_knowledge_signals,
        valuable_card_knowledge=valuable_card_knowledge,
        listing_quality=listing_quality,
        hidden_find=hidden_find,
        valuation_confidence_score=valuation_confidence_score,
        sold_comparable_count=sold_comparable_count,
        total_cost=total_cost,
        expected_resale=expected_resale,
        evidence_fusion=detail_evidence_fusion,
    )
    market_edge = compute_market_edge(
        item, hidden_find, listing_quality, features, risk_analysis
    )

    visual_edge = build_visual_edge(
        item,
        listing_quality_score=listing_quality.get("score", 0),
        hidden_find_score=hidden_find.get("score", 0),
        market_edge_score=market_edge.get("score", 0),
        identity_confidence_score=features.get("identity_confidence_score", 0),
        knowledge_signals=market_knowledge_signals,
    )

    flip_scenarios = build_flip_scenarios(
        total_cost=total_cost,
        floor_resale=floor_resale,
        expected_resale=expected_resale,
        best_case_resale=best_case_resale,
        liquidity_score=liquidity,
        sale_probability=probability,
    )

    opportunity_radar = compute_opportunity_radar({
        "beslut": decision,
        "deal_score": deal_score["score"],
        "market_edge_score": market_edge["score"],
        "risk_score": risk_analysis["score"],
        "valuation_confidence_score": valuation_confidence_score,
        "liquidity_score": liquidity,
        "sale_type": sale_type,
        "auction_bid_strategy": auction_strategy,
        "visual_edge_score": visual_edge["score"],
        "visual_verification_required": visual_edge["requires_visual_verification"],
    })

    # Kommentaren ska bygga på samma beräknade analysvärden
    # som returneras till användaren. Tidigare skickades originalannonsen
    # in här, vilket gjorde att build_comment ofta föll tillbaka på
    # standardvärden för efterfrågan, likviditet och riskjusterad vinst.
    comment_context = dict(item)
    comment_context.update({
        "demand_tier": profile["tier"],
        "sale_probability": probability,
        "liquidity_score": liquidity,
        "liquidity_level": liquidity_analysis.get("level"),
        "liquidity_label": liquidity_analysis.get("label"),
        "liquidity_evidence": liquidity_analysis.get("evidence"),
        "liquidity_sold_30d": liquidity_analysis.get("sold_30d", 0),
        "liquidity_sold_90d": liquidity_analysis.get("sold_90d", 0),
        "liquidity_reasons": liquidity_analysis.get("reasons", []),
        "risk_adjusted_profit": profits["risk_adjusted_profit"],
        "quick_flip_score": quick_score,
        "premium_flip_score": premium_score,
        "value_source": value_source,
        "comparable_count": comparable_count,
        "risk_flags": risks,
        "risk_score": risk_analysis["score"],
        "risk_level": risk_analysis["level"],
    })

    try:
        comment = build_comment(
            comment_context,
            expected_resale,
            confidence,
            reasons,
        )

    except Exception:
        comment = "; ".join(
            reasons[:3]
        )

    return {
        "titel": title,
        "pris": price,
        "frakt":
            item.get(
                "frakt"
            ),

        "total_cost":
            total_cost,

        "analysis_total_cost":
            analysis_total_cost,

        "auction_buffer":
            auction_buffer,

        "sale_type":
            sale_type,

        "decision_diagnostics":
            decision_diagnostics,

        "max_total_price":
            (max_purchase or {}).get("max_total_price"),

        "max_item_price":
            (max_purchase or {}).get("max_item_price"),

        "max_price_shipping_assumption":
            (max_purchase or {}).get("assumed_shipping"),
        "auction_bid_strategy": auction_strategy,

        "player_name":
            profile["name"],

        "player_market_score":
            profile["score"],

        "demand_tier":
            profile["tier"],

        "player_match_confidence": profile.get("match_confidence", "low"),
        "player_match_type": features.get("player_match_type", "none"),
        "is_lot": features.get("is_lot", False),
        "lot_count": features.get("lot_count"),
        "lot_confidence": features.get("lot_confidence", "none"),
        "listing_quality_score": listing_quality["score"],
        "listing_quality_level": listing_quality["level"],
        "listing_quality_warnings": listing_quality["warnings"],
        "listing_quality_blockers": listing_quality["blockers"],
        "extreme_discount_flag": extreme_discount,
        "deal_confidence_score": deal_confidence["score"],
        "deal_score": deal_score["score"],
        "deal_score_label": deal_score["label"],
        "deal_score_components": deal_score["components"],
        "deal_confidence_level": deal_confidence["level"],
        "deal_confidence_strengths": deal_confidence["strengths"],
        "deal_confidence_weaknesses": deal_confidence["weaknesses"],
        "deal_confidence_components": deal_confidence["components"],
        "comp_confidence": comp_confidence,
        "comp_valuation_basis": comp_valuation_basis,
        "valuation_confidence_score": valuation_confidence_score,
        "valuation_confidence_level": valuation_confidence_level,
        "valuation_confidence_reasons": valuation_confidence_reasons,
        "valuation_confidence_components": valuation_confidence_components,
        "sold_comparable_count": sold_comparable_count,
        "asking_comparable_count": asking_comparable_count,
        "comparable_details": comparable_details,
        "comp_valuation_range": comp_valuation_range,
        "rejected_comparable_count": rejected_comparable_count,
        "rejected_comparables": rejected_comparables,
        "card_identity_confidence": features.get("card_identity_confidence", "low"),
        "card_identity_confidence_score": features.get("identity_confidence_score", 0),
        "card_identity": features.get("card_identity"),
        "identity_evidence_sources": features.get("identity_evidence_sources", {}),
        "identity_enriched_fields": features.get("identity_enriched_fields", []),
        "identity_conflicts": features.get("identity_conflicts", []),
        "detail_evidence_fusion_score": detail_evidence_fusion.get("score", 0),
        "detail_evidence_fusion_status": detail_evidence_fusion.get("status"),
        "detail_evidence_fusion_source_count": detail_evidence_fusion.get("source_count", 0),
        "detail_evidence_fusion_corroborated_fields": detail_evidence_fusion.get("corroborated_fields", []),
        "detail_evidence_fusion_discoveries": detail_evidence_fusion.get("discoveries", []),
        "detail_evidence_fusion_conflicts": detail_evidence_fusion.get("conflicts", []),
        "detail_evidence_fusion_has_conflict": detail_evidence_fusion.get("has_conflict", False),
        "detail_evidence_fusion_note": detail_evidence_fusion.get("note"),
        "market_knowledge_signals": market_knowledge_signals,
        "card_intelligence_level": card_intelligence.get("level"),
        "card_intelligence_tier": card_intelligence.get("tier", 0),
        "card_intelligence_summary": card_intelligence.get("summary"),
        "card_intelligence_paths": card_intelligence.get("paths", []),
        "card_intelligence_reasons": card_intelligence.get("reasons", []),
        "card_intelligence_verification_steps": card_intelligence.get("verification_steps", []),
        "card_intelligence_source_ids": card_intelligence.get("source_ids", []),
        "card_knowledge_library_summary": card_knowledge_library.get("summary"),
        "card_knowledge_library_families": card_knowledge_library.get("families", []),
        "card_knowledge_library_comp_boundaries": card_knowledge_library.get("comp_boundaries", []),
        "card_knowledge_library_version": card_knowledge_library.get("library_version"),
        "card_knowledge_library_note": card_knowledge_library.get("note"),
        "variant_hierarchy_variant_rung": variant_hierarchy.get("variant_rung", 0),
        "variant_hierarchy_variant_label": variant_hierarchy.get("variant_label"),
        "variant_hierarchy_rookie_rung": variant_hierarchy.get("rookie_rung", 0),
        "variant_hierarchy_rookie_label": variant_hierarchy.get("rookie_label"),
        "variant_hierarchy_summary": variant_hierarchy.get("summary"),
        "variant_hierarchy_paths": variant_hierarchy.get("paths", []),
        "variant_hierarchy_reasons": variant_hierarchy.get("reasons", []),
        "variant_hierarchy_verification_steps": variant_hierarchy.get("verification_steps", []),
        "variant_hierarchy_note": variant_hierarchy.get("note"),
        "collector_intelligence_score": collector_intelligence.get("score", 0),
        "collector_intelligence_level": collector_intelligence.get("level"),
        "collector_intelligence_label": collector_intelligence.get("label"),
        "collector_intelligence_archetype": collector_intelligence.get("archetype"),
        "collector_intelligence_reasons": collector_intelligence.get("reasons", []),
        "collector_intelligence_cautions": collector_intelligence.get("cautions", []),
        "collector_intelligence_next_action": collector_intelligence.get("next_action"),
        "collector_intelligence_note": collector_intelligence.get("note"),
        "player_card_demand_score": player_card_demand.get("score", 0),
        "player_card_demand_confidence_score": player_card_demand.get("confidence_score", 0),
        "player_card_demand_profile": player_card_demand.get("profile"),
        "player_card_demand_review_priority_score": player_card_demand.get("review_priority_score", 0),
        "player_card_demand_preselection_boost": player_card_demand.get("preselection_boost", 0),
        "player_card_demand_player_component": player_card_demand.get("player_component", 0),
        "player_card_demand_structure_component": player_card_demand.get("structure_component", 0),
        "player_card_demand_market_component": player_card_demand.get("market_component", 0),
        "player_card_demand_market_evidence": player_card_demand.get("market_evidence"),
        "player_card_demand_reasons": player_card_demand.get("reasons", []),
        "player_card_demand_cautions": player_card_demand.get("cautions", []),
        "player_card_demand_next_action": player_card_demand.get("next_action"),
        "player_card_demand_note": player_card_demand.get("note"),
        "valuable_card_priority_score": valuable_card_knowledge.get("priority_score", 0),
        "valuable_card_level": valuable_card_knowledge.get("level"),
        "valuable_card_archetype": valuable_card_knowledge.get("archetype"),
        "valuable_card_tags": valuable_card_knowledge.get("tags", []),
        "valuable_card_structure_score": valuable_card_knowledge.get("structure_score", 0),
        "valuable_card_player_score": valuable_card_knowledge.get("player_score", 0),
        "valuable_card_market_evidence": valuable_card_knowledge.get("market_evidence"),
        "valuable_card_market_evidence_score": valuable_card_knowledge.get("market_evidence_score", 0),
        "valuable_card_reasons": valuable_card_knowledge.get("reasons", []),
        "valuable_card_cautions": valuable_card_knowledge.get("cautions", []),
        "valuable_card_note": valuable_card_knowledge.get("note"),
        "rookie_importance_matched": rookie_importance.get("matched", False),
        "rookie_importance_score": rookie_importance.get("importance_score", 0),
        "rookie_importance_tier": rookie_importance.get("tier"),
        "rookie_importance_status": rookie_importance.get("status"),
        "rookie_importance_key_status": rookie_importance.get("key_rookie_status"),
        "rookie_importance_reasons": rookie_importance.get("reasons", []),
        "rookie_importance_cautions": rookie_importance.get("cautions", []),
        "rookie_importance_next_action": rookie_importance.get("next_action"),
        "rookie_importance_safe_key": rookie_importance.get("safe_to_call_key_rookie", False),
        "rookie_importance_note": rookie_importance.get("note"),
        "mispriced_rookie_score": mispriced_rookie.get("score", 0),
        "mispriced_rookie_label": mispriced_rookie.get("label"),
        "mispriced_rookie_candidate": mispriced_rookie.get("candidate", False),
        "mispriced_rookie_price_gap_supported": mispriced_rookie.get("price_gap_supported", False),
        "mispriced_rookie_reasons": mispriced_rookie.get("reasons", []),
        "mispriced_rookie_cautions": mispriced_rookie.get("cautions", []),
        "mispriced_rookie_next_action": mispriced_rookie.get("next_action"),
        "mispriced_rookie_note": mispriced_rookie.get("note"),
        "misclassified_card_score": misclassified_card.get("score", 0),
        "misclassified_card_label": misclassified_card.get("label"),
        "misclassified_card_candidate": misclassified_card.get("candidate", False),
        "misclassified_card_price_gap_supported": misclassified_card.get("price_gap_supported", False),
        "misclassified_card_target_tags": misclassified_card.get("target_tags", []),
        "misclassified_card_reasons": misclassified_card.get("reasons", []),
        "misclassified_card_cautions": misclassified_card.get("cautions", []),
        "misclassified_card_next_action": misclassified_card.get("next_action"),
        "misclassified_card_note": misclassified_card.get("note"),
        "chase_knowledge_priority_score": chase_knowledge_graph.get("priority_score", 0),
        "chase_knowledge_level": chase_knowledge_graph.get("level"),
        "chase_knowledge_profile": chase_knowledge_graph.get("profile"),
        "chase_knowledge_reasons": chase_knowledge_graph.get("reasons", []),
        "chase_knowledge_verification_steps": chase_knowledge_graph.get("verification_steps", []),
        "chase_knowledge_nodes": chase_knowledge_graph.get("nodes", []),
        "chase_knowledge_edges": chase_knowledge_graph.get("edges", []),
        "chase_knowledge_source_ids": chase_knowledge_graph.get("source_ids", []),
        "chase_knowledge_note": chase_knowledge_graph.get("note"),
        "hidden_find_score": hidden_find["score"],
        "hidden_find_label": hidden_find["label"],
        "hidden_find_reasons": hidden_find["reasons"],
        "is_hidden_find_candidate": hidden_find["is_hidden_candidate"],
        "market_edge_score": market_edge["score"],
        "market_edge_label": market_edge["label"],
        "market_edge_reasons": market_edge["reasons"],
        "market_edge_types": market_edge["types"],
        "is_market_edge_candidate": market_edge["is_edge_candidate"],
        "visual_edge_score": visual_edge["score"],
        "visual_edge_label": visual_edge["label"],
        "visual_edge_reasons": visual_edge["reasons"],
        "visual_image_count": visual_edge["image_count"],
        "visual_image_urls": visual_edge["image_urls"],
        "visual_metadata_terms": visual_edge["metadata_terms"],
        "visual_verification_required": visual_edge["requires_visual_verification"],
        "opportunity_action": opportunity_radar["action"],
        "opportunity_priority_score": opportunity_radar["priority_score"],
        "opportunity_reasons": opportunity_radar["reasons"],
        "flip_scenarios": flip_scenarios.get("scenarios", []),
        "flip_scenario_summary": flip_scenarios.get("summary"),
        "flip_scenario_resilient": flip_scenarios.get("resilient_flip", False),
        "flip_scenario_note": flip_scenarios.get("note"),

        "sport":
            sport,

        "score":
            item.get(
                "score",
                0,
            )
            or 0,

        "uppskattat_varde":
            expected_resale,

        "heuristic_estimated_value":
            heuristic,

        "comp_estimated_value":
            (
                round(
                    comp_value
                )
                if comp_value
                is not None
                else None
            ),

        "value_source":
            value_source,

        "marginal":
            expected_resale
            - total_cost,

        "confidence":
            round(
                confidence,
                2,
            ),

        "rank_score":
            rank,

        "base_rank_score":
            base_rank,

        "ranking_confidence_score":
            ranking_confidence,

        "card_quality_score":
            quality,

        "hype_score":
            profile["score"],

        "specificity_score":
            specificity,

        "listing_weakness_score":
            max(
                0,
                100
                - specificity,
            ),

        "mislist_potential":
            max(
                0,
                70
                - specificity,
            ),

        "liquidity_score":
            liquidity,

        "sale_probability":
            probability,

        "uncertainty_haircut":
            haircut,

        "floor_resale":
            floor_resale,

        "expected_resale":
            expected_resale,

        "best_case_resale":
            best_case_resale,

        "net_profit_estimate":
            profits[
                "net_profit_estimate"
            ],

        "floor_profit_estimate":
            profits[
                "floor_profit_estimate"
            ],

        "risk_adjusted_profit":
            profits[
                "risk_adjusted_profit"
            ],

        "quick_flip_score":
            quick_score,

        "premium_flip_score":
            premium_score,

        "exit_speed":
            compute_exit_speed(
                liquidity,
                probability,
                total_cost,
            ),

        "roi_estimate":
            profits[
                "roi_estimate"
            ],

        "beslut":
            decision,

        "kommentar":
            comment,

        "lank":
            item.get(
                "lank",
                "",
            ),

        "sale_type":
            sale_type,

        "reasons":
            reasons,

        "risk_flags":
            risks,

        "market_analysis_summary":
            market_summary,

        "comparable_count":
            comparable_count,

        "saljare":
            item.get(
                "saljare"
            ),

        "source_category":
            item.get(
                "source_category"
            ),
    }


def analyze_item_fast(
    item,
    strategy_mode="quick_flip",
    sport="hockey",
):
    return analyze_core(
        item,
        sport=sport,
        strategy_mode=strategy_mode,
        all_items=None,
        full=False,
    )


def analyze_item_full(
    item,
    all_items=None,
    strategy_mode="quick_flip",
    sport="hockey",
):
    return analyze_core(
        item,
        sport=sport,
        strategy_mode=strategy_mode,
        all_items=(
            all_items
            or []
        ),
        full=True,
    )



def compute_opportunity_radar(result):
    """Turn a completed analysis into a small action queue.

    This layer never changes valuation, profit, max price or the underlying BUY
    decision. It only prioritises what the user should do next.
    """
    decision = str(result.get("beslut") or "SKIP")
    deal = float(result.get("deal_score") or 0)
    edge = float(result.get("market_edge_score") or 0)
    visual_edge = float(result.get("visual_edge_score") or 0)
    visual_required = bool(result.get("visual_verification_required"))
    risk = float(result.get("risk_score") or 100)
    valuation = float(result.get("valuation_confidence_score") or 0)
    liquidity = float(result.get("liquidity_score") or 0)
    sale_type = str(result.get("sale_type") or "").lower()
    strategy = result.get("auction_bid_strategy") or {}
    auction_status = str(strategy.get("status") or "").upper()

    reasons = []
    if decision in {"KÖP", "KÖP (starkt fynd)"} and deal >= 68 and risk <= 55 and valuation >= 45:
        action = "AGERA NU"
        priority = 90 + min(10, (deal - 68) * 0.25)
        reasons.append("klarar FlipFynds köpgräns med stark fyndpoäng")
        if "auktion" in sale_type and auction_status in {"AVVAKTA", "BEVAKA"}:
            action = "BEVAKA"
            priority -= 12
            reasons.append("auktionen är ännu inte i ett läge där ett bud behövs")
    elif decision in {"KÖP", "KÖP (starkt fynd)", "KANSKE"} and deal >= 52 and risk <= 70:
        action = "BEVAKA"
        priority = 65 + min(20, (deal - 52) * 0.6)
        reasons.append("intressant ekonomi men inte tillräckligt stark för omedelbar åtgärd")
    elif edge >= 60 or visual_edge >= 60 or (deal >= 42 and (valuation < 45 or risk > 60)):
        action = "UNDERSÖK"
        priority = 45 + min(20, max(edge, visual_edge) * 0.2)
        if visual_edge >= 60:
            reasons.append("annonsbilderna bör granskas – texten räcker inte för säker identifiering")
        elif edge >= 60:
            reasons.append("möjlig informations- eller sökbarhetsedge behöver verifieras")
        else:
            reasons.append("potential finns men underlaget är för osäkert")
    else:
        action = "IGNORERA"
        priority = min(40, deal * 0.35 + edge * 0.15)
        reasons.append("för svag kombination av potential och bevisläge")

    if risk >= 75 and action in {"AGERA NU", "BEVAKA"}:
        action = "UNDERSÖK"
        priority = min(priority, 62)
        reasons.append("hög risk kräver manuell kontroll före köp")
    if valuation < 30 and action == "AGERA NU":
        action = "UNDERSÖK"
        priority = min(priority, 60)
        reasons.append("värderingssäkerheten är för låg för direkt köp")
    if auction_status == "STOPP":
        action = "IGNORERA"
        priority = min(priority, 30)
        reasons.append("auktionen har nått eller passerat FlipFynds budtak")

    priority += max(-5, min(5, (liquidity - 50) * 0.08))
    return {"action": action, "priority_score": round(max(0, min(100, priority)), 1), "reasons": reasons[:3]}

def analyze_item(
    item,
    all_items=None,
    mode="full",
    strategy_mode="quick_flip",
    sport="hockey",
):
    if mode == "fast":
        return analyze_item_fast(
            item,
            strategy_mode=
                strategy_mode,
            sport=sport,
        )

    return analyze_item_full(
        item,
        all_items=all_items,
        strategy_mode=
            strategy_mode,
        sport=sport,
    )