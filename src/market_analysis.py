import statistics
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import List, Optional

from src.card_parser import build_card_identity, parse_card_features
from src.pricing import total_acquisition_cost

PREMIUM_SETS = {
    'The Cup', 'SP Authentic', 'Dominion', 'Premier', 'Ultimate Collection', 'Black Diamond',
    'Topps Chrome', 'Topps Finest', 'Topps Merlin', 'Panini Prizm', 'Panini Select',
    'Topps Museum', 'Obsidian', 'Immaculate', 'National Treasures'
}


def _safe_total_cost(item: dict) -> Optional[float]:
    """Use the same acquisition-cost rule as the main analyzer.

    Missing/invalid shipping must never silently become 0 in comp analysis,
    otherwise local comparison prices look artificially cheap relative to the
    main ranking.
    """
    total = total_acquisition_cost(item.get("pris"), item.get("frakt"))
    return float(total) if total is not None else None


def _normalize_features(item: dict) -> dict:
    title = item.get("titel", "") or ""
    features = parse_card_features(title)

    player_name = features.get("player_name")
    if player_name:
        aliases = {
            "Connor Mcdavid": "Connor McDavid",
            "Nathan Mackinnon": "Nathan MacKinnon",
            "Nils Hoglander": "Nils Hoglander",
        }
        features["player_name"] = aliases.get(player_name, player_name)

    features.update(build_card_identity(features))
    return features


def _same_last_name(name1: Optional[str], name2: Optional[str]) -> bool:
    if not name1 or not name2:
        return False

    parts1 = name1.split()
    parts2 = name2.split()
    if not parts1 or not parts2:
        return False

    return parts1[-1].lower() == parts2[-1].lower()


def _is_premium(features: dict) -> bool:
    return (
        features.get("set_name") in PREMIUM_SETS
        or features.get("is_auto")
        or features.get("is_patch")
        or features.get("is_low_serial")
    )


def _serial_bucket(features: dict) -> str:
    serial = features.get("serial_number")

    if serial is None:
        return "none"
    if serial <= 10:
        return "ultra_low"
    if serial <= 25:
        return "very_low"
    if serial <= 50:
        return "low"
    if serial <= 99:
        return "mid_low"
    if serial <= 199:
        return "mid"
    if serial <= 499:
        return "high"
    return "very_high"




def assess_comp_compatibility(base_item: dict, other_item: dict) -> dict:
    """Hard guardrails for fields that define the exact card variant.

    A comp is rejected only when both listings explicitly identify a field and
    those values conflict. Missing information stays uncertain rather than being
    invented. This keeps near-comps available while preventing clearly different
    cards from contaminating the valuation.
    """
    base = _normalize_features(base_item)
    other = _normalize_features(other_item)
    blockers = []

    def explicit_conflict(field, label):
        a = base.get(field)
        b = other.get(field)
        if a not in (None, "") and b not in (None, "") and a != b:
            blockers.append(f"{label}: {a} ≠ {b}")

    # Checklist number and season identify different cards/issues when both are known.
    explicit_conflict("card_number", "kortnummer")
    explicit_conflict("season", "säsong")

    # Serial denominator (/25, /99 etc.) materially changes scarcity/value.
    explicit_conflict("serial_number", "serial numbering")

    # Graded cards with explicitly different grades are not direct price comps.
    base_grade = str(base.get("grade") or "").strip().upper()
    other_grade = str(other.get("grade") or "").strip().upper()
    if base_grade and other_grade and base_grade != other_grade:
        blockers.append(f"grade: {base_grade} ≠ {other_grade}")

    # Named parallels are variant-defining. Only reject when both are explicitly
    # identified; absence on one side is uncertainty, not evidence of base version.
    base_parallel = str(base.get("parallel") or "").strip().casefold()
    other_parallel = str(other.get("parallel") or "").strip().casefold()
    if base_parallel and other_parallel and base_parallel != other_parallel:
        blockers.append(f"parallel: {base.get('parallel')} ≠ {other.get('parallel')}")

    return {
        "eligible": not blockers,
        "blockers": blockers,
    }

def score_similarity(base_item: dict, other_item: dict) -> int:
    if base_item.get("lank") == other_item.get("lank"):
        return -999

    base_features = _normalize_features(base_item)
    other_features = _normalize_features(other_item)

    score = 0

    base_player = base_features.get("player_name")
    other_player = other_features.get("player_name")

    if base_player and other_player:
        if base_player == other_player:
            score += 24
        elif _same_last_name(base_player, other_player):
            score += 4
        else:
            score -= 18
    elif bool(base_player) != bool(other_player):
        score -= 8

    base_set = base_features.get("set_name")
    other_set = other_features.get("set_name")

    if base_set and other_set:
        if base_set == other_set:
            score += 14
        else:
            score -= 10
    elif bool(base_set) != bool(other_set):
        score -= 5

    base_year = base_features.get("year")
    other_year = other_features.get("year")
    base_season = base_features.get("season")
    other_season = other_features.get("season")

    if base_season and other_season:
        if base_season == other_season:
            score += 8
        else:
            score -= 6
    elif base_year and other_year:
        if base_year == other_year:
            score += 5
        elif abs(base_year - other_year) == 1:
            score += 1
        elif abs(base_year - other_year) >= 3:
            score -= 4

    base_card_number = base_features.get("card_number")
    other_card_number = other_features.get("card_number")

    if base_card_number and other_card_number:
        if base_card_number == other_card_number:
            score += 16
        else:
            # Same player/set but a different checklist number is usually a
            # different card and should not be treated as an exact comp.
            score -= 14
    elif bool(base_card_number) != bool(other_card_number):
        score -= 4

    base_parallel = base_features.get("parallel")
    other_parallel = other_features.get("parallel")

    if base_parallel and other_parallel:
        if base_parallel == other_parallel:
            score += 6
        else:
            score -= 6
    elif bool(base_parallel) != bool(other_parallel):
        score -= 3

    # Treat product + rookie program + named parallel as one identity. This is
    # especially important for cards such as Young Guns Outburst or Prizm Silver
    # Rookie, where same-player/same-set base cards are weak price comparisons.
    base_identity = base_features.get("card_identity_key")
    other_identity = other_features.get("card_identity_key")
    base_family = base_features.get("card_identity_family")
    other_family = other_features.get("card_identity_family")
    if base_identity and other_identity and base_identity == other_identity:
        score += 12
    elif base_family and other_family and base_family == other_family:
        # Same family but a different named parallel/trait is related, not exact.
        if base_parallel != other_parallel and (base_parallel or other_parallel):
            score -= 8
        else:
            score += 3
    elif base_family and other_family and base_family != other_family:
        score -= 5

    base_rookie_variant = base_features.get("rookie_variant")
    other_rookie_variant = other_features.get("rookie_variant")
    if base_rookie_variant and other_rookie_variant:
        if base_rookie_variant == other_rookie_variant:
            score += 4
        elif "Generic Rookie" not in {base_rookie_variant, other_rookie_variant}:
            score -= 6

    if base_features.get("is_rookie") == other_features.get("is_rookie"):
        score += 4
    else:
        score -= 5

    if base_features.get("is_auto") == other_features.get("is_auto"):
        score += 6
    else:
        score -= 8

    if base_features.get("is_patch") == other_features.get("is_patch"):
        score += 4
    else:
        score -= 5

    if base_features.get("is_graded") == other_features.get("is_graded"):
        score += 5
    else:
        score -= 8

    if base_features.get("is_lot") == other_features.get("is_lot"):
        score += 2
    else:
        score -= 16

    base_premium = _is_premium(base_features)
    other_premium = _is_premium(other_features)
    if base_premium == other_premium:
        score += 4
    else:
        score -= 8

    base_serial_bucket = _serial_bucket(base_features)
    other_serial_bucket = _serial_bucket(other_features)
    if base_serial_bucket == other_serial_bucket:
        score += 6
    elif base_serial_bucket == "none" or other_serial_bucket == "none":
        score -= 2
    else:
        score -= 6

    base_serial = base_features.get("serial_number")
    other_serial = other_features.get("serial_number")
    if base_serial is not None and other_serial is not None:
        if base_serial == other_serial:
            score += 4
        elif abs(base_serial - other_serial) <= 10:
            score += 2
        elif abs(base_serial - other_serial) >= 200:
            score -= 4

    return score



def _normalized_listing_title(item: dict) -> str:
    title = str(item.get("titel") or "").casefold()
    title = re.sub(r"[^a-z0-9åäö]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def _likely_same_listing(a: dict, b: dict) -> bool:
    """Treat relists as one comp source, without deleting legitimate inventory."""
    if a.get("lank") and a.get("lank") == b.get("lank"):
        return True

    total_a = _safe_total_cost(a)
    total_b = _safe_total_cost(b)
    if total_a is None or total_b is None:
        return False
    if abs(total_a - total_b) / max(total_a, total_b, 1.0) > 0.08:
        return False

    seller_a = str(a.get("saljare") or "").casefold().strip()
    seller_b = str(b.get("saljare") or "").casefold().strip()
    same_seller = bool(seller_a and seller_b and seller_a == seller_b)

    fa = _normalize_features(a)
    fb = _normalize_features(b)
    identity_a = fa.get("card_identity_key")
    identity_b = fb.get("card_identity_key")
    same_identity = bool(identity_a and identity_b and identity_a == identity_b)

    ta = _normalized_listing_title(a)
    tb = _normalized_listing_title(b)
    ratio = SequenceMatcher(None, ta, tb).ratio() if ta and tb else 0.0

    if same_seller and (same_identity or ratio >= 0.82):
        return True
    if not same_seller and same_identity and ratio >= 0.94:
        return True
    return False


def _dedupe_comparables(scored_items):
    unique = []
    for score, item in scored_items:
        if any(_likely_same_listing(item, existing) for _, existing in unique):
            continue
        unique.append((score, item))
    return unique


def _dedupe_sold_comparables(scored_items):
    """Be conservative about deleting realised sales.

    Two different sellers can genuinely sell the same card at almost the same
    price, so cross-seller sold records must remain separate observations.
    Only identical URLs or likely relists from the same seller are collapsed.
    """
    unique = []
    for score, item in scored_items:
        duplicate = False
        for _, existing in unique:
            if item.get("lank") and item.get("lank") == existing.get("lank"):
                duplicate = True
                break
            seller_a = str(item.get("saljare") or "").casefold().strip()
            seller_b = str(existing.get("saljare") or "").casefold().strip()
            if seller_a and seller_b and seller_a == seller_b and _likely_same_listing(item, existing):
                duplicate = True
                break
        if not duplicate:
            unique.append((score, item))
    return unique

def _filter_by_price_distance(base_total_cost: float, candidates: List[dict]) -> List[dict]:
    filtered = []

    for item in candidates:
        total_cost = _safe_total_cost(item)
        if total_cost is None:
            continue

        if base_total_cost <= 100:
            if total_cost <= max(base_total_cost * 2.4, 180):
                filtered.append(item)
        elif base_total_cost <= 300:
            if total_cost <= base_total_cost * 2.2 and total_cost >= base_total_cost * 0.35:
                filtered.append(item)
        else:
            if total_cost <= base_total_cost * 2.0 and total_cost >= base_total_cost * 0.40:
                filtered.append(item)

    return filtered


def _remove_outliers(prices: List[float]) -> List[float]:
    if len(prices) < 4:
        return prices

    sorted_prices = sorted(prices)
    q1 = statistics.median(sorted_prices[: len(sorted_prices) // 2])
    if len(sorted_prices) % 2 == 0:
        upper_half = sorted_prices[len(sorted_prices) // 2 :]
    else:
        upper_half = sorted_prices[len(sorted_prices) // 2 + 1 :]
    q3 = statistics.median(upper_half) if upper_half else q1

    iqr = q3 - q1
    if iqr == 0:
        return sorted_prices

    low_bound = q1 - 1.5 * iqr
    high_bound = q3 + 1.5 * iqr

    cleaned = [p for p in sorted_prices if low_bound <= p <= high_bound]
    return cleaned if cleaned else sorted_prices


def _trimmed_median(prices: List[float]) -> float:
    if not prices:
        return 0.0

    sorted_prices = sorted(prices)
    n = len(sorted_prices)

    if n <= 4:
        return float(statistics.median(sorted_prices))

    trim = max(1, int(round(n * 0.15)))
    if n - (trim * 2) < 2:
        return float(statistics.median(sorted_prices))

    trimmed = sorted_prices[trim : n - trim]
    return float(statistics.median(trimmed))


def _parse_datetime(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        text = text.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    dt = None
            if dt is None:
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _market_state(item: dict) -> str:
    """Return sold/asking without guessing from an ended auction alone.

    A listing is only treated as a realised sale when the input data explicitly
    says it sold or carries an explicit sold price. Ended/closed is not enough.
    """
    explicit_sold_price = item.get("sold_price")
    if isinstance(explicit_sold_price, (int, float)) and explicit_sold_price > 0:
        return "sold"

    raw_values = [
        item.get("market_state"),
        item.get("listing_status"),
        item.get("sale_status"),
        item.get("status"),
    ]
    normalized = " ".join(str(v or "").casefold().strip() for v in raw_values)
    sold_markers = {"sold", "såld", "completed_sold", "ended_sold", "realized", "realised"}
    if any(marker in normalized.split() for marker in sold_markers):
        return "sold"
    if any(marker in normalized for marker in ("completed sold", "ended sold", "avslutad såld")):
        return "sold"
    return "asking"


def _realized_total(item: dict) -> Optional[float]:
    """Price actually paid by the buyer when known.

    Prefer an explicit all-in sold total. Otherwise use sold price plus known
    shipping. Missing shipping is *not* invented for sold comps because that
    would fabricate a realised amount. In that case the sold item price itself
    is used and provenance stays visible in comparable_details.
    """
    explicit_total = item.get("sold_total_price")
    if isinstance(explicit_total, (int, float)) and explicit_total > 0:
        return float(explicit_total)

    sold_price = item.get("sold_price")
    if not isinstance(sold_price, (int, float)) or sold_price <= 0:
        sold_price = item.get("pris")
    if not isinstance(sold_price, (int, float)) or sold_price <= 0:
        return None

    shipping = item.get("frakt")
    if isinstance(shipping, (int, float)) and shipping >= 0:
        return float(sold_price + shipping)
    return float(sold_price)


def _comp_date(item: dict):
    for key in ("sold_at", "sale_date", "ended_at", "end_date", "published_at"):
        dt = _parse_datetime(item.get(key))
        if dt is not None:
            return dt
    return None


def _age_days(item: dict, now=None):
    dt = _comp_date(item)
    if dt is None:
        return None
    now = now or datetime.now(timezone.utc)
    return max(0, (now - dt).days)


def _age_weight(age_days):
    if age_days is None:
        return 0.75
    if age_days <= 30:
        return 1.00
    if age_days <= 90:
        return 0.90
    if age_days <= 180:
        return 0.78
    if age_days <= 365:
        return 0.62
    return 0.45


def _match_label(similarity: int) -> str:
    if similarity >= 62:
        return "mycket hög"
    if similarity >= 48:
        return "hög"
    if similarity >= 34:
        return "medel"
    return "låg"


def _source_platform(item: dict) -> str:
    value = item.get("platform") or item.get("source_platform") or "Tradera"
    return str(value).strip() or "Tradera"


def _comp_confidence(comparable_count: int, similarity_scores: List[int], *, basis="asking", ages=None) -> str:
    ages = [a for a in (ages or []) if a is not None]
    median_similarity = statistics.median(similarity_scores) if similarity_scores else 0
    median_age = statistics.median(ages) if ages else None

    if basis == "sold":
        if comparable_count >= 4 and median_similarity >= 42 and (median_age is None or median_age <= 180):
            return "hög"
        if comparable_count >= 2 and median_similarity >= 30 and (median_age is None or median_age <= 365):
            return "medel"
        return "låg"

    if comparable_count >= 8 and median_similarity >= 34:
        return "hög"
    if comparable_count >= 5 and median_similarity >= 28:
        return "medel"
    return "låg"


def _weighted_median(pairs):
    """Weighted median for (value, weight) pairs."""
    pairs = sorted((float(v), max(0.0, float(w))) for v, w in pairs if v is not None and w > 0)
    if not pairs:
        return 0.0
    total_weight = sum(w for _, w in pairs)
    halfway = total_weight / 2.0
    running = 0.0
    for value, weight in pairs:
        running += weight
        if running >= halfway:
            return value
    return pairs[-1][0]


def _comparable_detail(similarity: int, item: dict, state: str) -> dict:
    price = _realized_total(item) if state == "sold" else _safe_total_cost(item)
    age = _age_days(item)
    return {
        "title": item.get("titel", ""),
        "url": item.get("lank", ""),
        "platform": _source_platform(item),
        "market_state": state,
        "price": round(float(price), 2) if price is not None else None,
        "sold_price": item.get("sold_price") if state == "sold" else None,
        "shipping": item.get("frakt"),
        "date": (_comp_date(item).date().isoformat() if _comp_date(item) else None),
        "age_days": age,
        "similarity_score": similarity,
        "match_quality": _match_label(similarity),
        "provenance": item.get("provenance") or item.get("source") or _source_platform(item),
    }


def _price_stats(values: List[float]) -> dict:
    if not values:
        return {}
    cleaned = _remove_outliers(values)
    return {
        "low": round(float(min(cleaned)), 2),
        "median": round(float(statistics.median(cleaned)), 2),
        "high": round(float(max(cleaned)), 2),
        "trimmed_median": round(float(_trimmed_median(cleaned)), 2),
    }




def _percentile(values: List[float], percentile: float) -> Optional[float]:
    """Linear percentile without numpy; used only for observed comp ranges."""
    if not values:
        return None
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return ordered[0]
    pct = max(0.0, min(1.0, float(percentile)))
    position = (len(ordered) - 1) * pct
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _valuation_range(values: List[float], base_value: Optional[float], confidence: str, basis: str) -> Optional[dict]:
    """Observed low/base/high range with explicit evidence label.

    This is never generated from thin air: sold ranges require at least two
    realised prices; asking ranges are labelled only as asking-price support.
    """
    if len(values) < 2 or base_value is None:
        return None
    cleaned = _remove_outliers(values)
    if len(cleaned) < 2:
        cleaned = values
    low = _percentile(cleaned, 0.25)
    high = _percentile(cleaned, 0.75)
    base = float(base_value)
    if low is None or high is None:
        return None
    low = min(float(low), base)
    high = max(float(high), base)
    return {
        "low": round(low, 2),
        "base": round(base, 2),
        "high": round(high, 2),
        "confidence": confidence,
        "basis": basis,
        "label": "realiserade försäljningar" if basis == "sold" else "aktiva begärda priser",
    }

def _price_dispersion_score(values: List[float]) -> tuple[float, Optional[float]]:
    """Return (0..100 stability score, relative median absolute deviation)."""
    cleaned = _remove_outliers([float(v) for v in values if v is not None and v > 0])
    if len(cleaned) < 2:
        return 30.0, None
    median = float(statistics.median(cleaned))
    if median <= 0:
        return 20.0, None
    deviations = [abs(v - median) for v in cleaned]
    mad_ratio = float(statistics.median(deviations)) / median
    if mad_ratio <= 0.08:
        return 100.0, mad_ratio
    if mad_ratio <= 0.15:
        return 85.0, mad_ratio
    if mad_ratio <= 0.25:
        return 65.0, mad_ratio
    if mad_ratio <= 0.40:
        return 40.0, mad_ratio
    return 20.0, mad_ratio


def compute_valuation_confidence(*, basis: str, values: List[float], similarity_scores: List[int], ages=None, rejected_count: int = 0) -> dict:
    """Independent confidence model for the monetary valuation.

    This is deliberately separate from overall deal confidence. It measures the
    evidence behind the *price estimate*: realised-vs-asking basis, sample size,
    match quality, recency, price dispersion and rejected-comp pressure.
    """
    basis = str(basis or "none").casefold()
    count = len(values or [])
    ages = [a for a in (ages or []) if a is not None]
    sims = [float(v) for v in (similarity_scores or [])]
    reasons = []
    components = {}

    if basis == "none" or count == 0:
        return {
            "score": 10, "level": "mycket låg",
            "reasons": ["inga användbara marknadscomps"],
            "components": {"basis": 0, "sample": 0, "match": 0, "recency": 0, "stability": 0, "rejections": 100},
        }

    if basis == "sold":
        basis_score = 100
        reasons.append("värderingen bygger på realiserade försäljningar")
    else:
        basis_score = 45
        reasons.append("värderingen bygger endast på aktiva begärda priser")

    if basis == "sold":
        sample_score = min(100.0, 35.0 + count * 13.0)
    else:
        sample_score = min(75.0, 20.0 + count * 7.0)
    if count < 3:
        reasons.append("få jämförelseobjekt")

    median_sim = statistics.median(sims) if sims else 0.0
    match_score = max(10.0, min(100.0, (median_sim - 18.0) * 2.0))
    if median_sim >= 48:
        reasons.append("hög median-matchning mot kortet")
    elif median_sim < 34:
        reasons.append("jämförelserna är bara måttligt lika")

    if basis == "sold":
        if ages:
            median_age = float(statistics.median(ages))
            if median_age <= 30:
                recency_score = 100.0
            elif median_age <= 90:
                recency_score = 90.0
            elif median_age <= 180:
                recency_score = 75.0
            elif median_age <= 365:
                recency_score = 55.0
            else:
                recency_score = 30.0
            if median_age > 365:
                reasons.append("försäljningarna är gamla")
        else:
            recency_score = 55.0
            reasons.append("försäljningsdatum saknas för flera comps")
    else:
        recency_score = 45.0

    stability_score, mad_ratio = _price_dispersion_score(values)
    if mad_ratio is not None and mad_ratio > 0.25:
        reasons.append("stor prisvariation mellan jämförelserna")

    rejection_ratio = rejected_count / max(1, rejected_count + count)
    rejection_score = max(20.0, 100.0 - rejection_ratio * 120.0)
    if rejected_count >= 2 and rejection_ratio >= 0.35:
        reasons.append("många potentiella comps diskvalificerades som fel variant")

    weights = {"basis": 0.28, "sample": 0.18, "match": 0.22, "recency": 0.12, "stability": 0.15, "rejections": 0.05}
    components = {
        "basis": round(basis_score), "sample": round(sample_score), "match": round(match_score),
        "recency": round(recency_score), "stability": round(stability_score), "rejections": round(rejection_score),
    }
    score = sum(components[k] * weights[k] for k in weights)

    # Asking prices can support a range but cannot earn sold-level certainty.
    if basis != "sold":
        score = min(score, 55.0)
    if basis == "sold" and count == 1:
        score = min(score, 45.0)

    score = int(round(max(0.0, min(100.0, score))))
    if score >= 80:
        level = "hög"
    elif score >= 60:
        level = "medel"
    elif score >= 40:
        level = "låg"
    else:
        level = "mycket låg"
    return {"score": score, "level": level, "reasons": reasons[:5], "components": components}


def build_market_analysis(item: dict, all_items: list) -> dict:
    current_price = item.get("pris")
    current_total_cost = _safe_total_cost(item)

    if current_price is None or current_price <= 0 or current_total_cost is None:
        return {"success": False, "error": "Objektet saknar giltigt pris."}

    if not all_items:
        return {
            "success": True,
            "comparable_count": 0,
            "sold_comparable_count": 0,
            "asking_comparable_count": 0,
            "summary": "Ingen lokal data att jämföra mot.",
            "price_stats": None,
            "sample_titles": [],
            "comparable_details": [],
            "valuation_basis": "none",
            "valuation_range": None,
            "rejected_comparable_count": 0,
            "rejected_comparables": [],
            "verdict": "För lite data.",
            "confidence": "låg",
            "valuation_confidence_score": 10,
            "valuation_confidence_level": "mycket låg",
            "valuation_confidence_reasons": ["inga användbara marknadscomps"],
            "valuation_confidence_components": {},
        }

    scored = []
    rejected_comps = []
    for other in all_items:
        if not isinstance(other, dict):
            continue
        state = _market_state(other)
        comp_price = _realized_total(other) if state == "sold" else _safe_total_cost(other)
        if comp_price is None:
            continue
        compatibility = assess_comp_compatibility(item, other)
        if not compatibility["eligible"]:
            rejected_comps.append({
                "title": other.get("titel", ""),
                "market_state": state,
                "reasons": compatibility["blockers"],
            })
            continue
        sim = score_similarity(item, other)
        if sim >= 22:
            scored.append((sim, other, state))

    scored.sort(key=lambda x: (-x[0], abs(((_realized_total(x[1]) if x[2] == "sold" else _safe_total_cost(x[1])) or 0) - current_total_cost)))

    # Price-distance filtering is useful for asking prices, but sold evidence
    # should not be discarded merely because the target listing itself is wildly
    # underpriced — that is exactly the situation FlipFynd is trying to detect.
    asking_rough = [x for x in scored if x[2] == "asking"]
    asking_candidates = _filter_by_price_distance(current_total_cost, [x[1] for x in asking_rough[:30]])
    asking_links = {id(x) for x in asking_candidates}

    rescored = []
    for sim, other, state in scored:
        if state == "asking" and id(other) not in asking_links:
            continue
        rescored.append((sim, other, state))

    # Deduplicate sold and asking pools separately. A historical sold record and
    # a later active relist must never collapse into one evidence type.
    sold_scored = _dedupe_sold_comparables([(s, i) for s, i, state in rescored if state == "sold"])
    asking_scored = _dedupe_comparables([(s, i) for s, i, state in rescored if state == "asking"])
    sold_scored = sold_scored[:10]
    asking_scored = asking_scored[:10]

    sold_values = []
    sold_similarity = []
    sold_ages = []
    sold_weighted = []
    for sim, comp in sold_scored:
        value = _realized_total(comp)
        if value is None:
            continue
        age = _age_days(comp)
        match_weight = max(0.25, min(1.0, sim / 65.0))
        weight = match_weight * _age_weight(age)
        sold_values.append(float(value))
        sold_similarity.append(sim)
        if age is not None:
            sold_ages.append(age)
        sold_weighted.append((float(value), weight))

    asking_values = []
    asking_similarity = []
    for sim, comp in asking_scored:
        value = _safe_total_cost(comp)
        if value is None:
            continue
        asking_values.append(float(value))
        asking_similarity.append(sim)

    sold_count = len(sold_values)
    asking_count = len(asking_values)
    details = [
        *[_comparable_detail(sim, comp, "sold") for sim, comp in sold_scored if _realized_total(comp) is not None],
        *[_comparable_detail(sim, comp, "asking") for sim, comp in asking_scored if _safe_total_cost(comp) is not None],
    ]

    valuation_basis = "none"
    benchmark_total = None
    confidence = "låg"
    price_stats = {
        "current_price": round(float(current_price), 2),
        "current_total_cost": round(current_total_cost, 2),
    }
    valuation_range = None

    if sold_count >= 2:
        valuation_basis = "sold"
        confidence = _comp_confidence(sold_count, sold_similarity, basis="sold", ages=sold_ages)
        weighted = _weighted_median(sold_weighted)
        sold_stats = _price_stats(sold_values)
        benchmark_total = weighted or sold_stats.get("trimmed_median") or sold_stats.get("median")
        valuation_range = _valuation_range(sold_values, benchmark_total, confidence, "sold")
        price_stats.update({
            "sold_low": sold_stats.get("low"),
            "sold_median": sold_stats.get("median"),
            "sold_high": sold_stats.get("high"),
            "sold_weighted_median": round(float(benchmark_total), 2) if benchmark_total else None,
            # Compatibility field consumed by analyzer.get_comp_info.
            "median_comparable_total_cost": round(float(benchmark_total), 2) if benchmark_total else None,
            "median_comparable_price": sold_stats.get("median"),
        })
    elif asking_count >= 2:
        valuation_basis = "asking"
        confidence = _comp_confidence(asking_count, asking_similarity, basis="asking")
        asking_stats = _price_stats(asking_values)
        benchmark_total = asking_stats.get("trimmed_median") or asking_stats.get("median")
        if confidence == "låg" and asking_stats.get("median") is not None and benchmark_total is not None:
            benchmark_total = min(asking_stats["median"], benchmark_total)
        valuation_range = _valuation_range(asking_values, benchmark_total, confidence, "asking")
        price_stats.update({
            "asking_low": asking_stats.get("low"),
            "asking_median": asking_stats.get("median"),
            "asking_high": asking_stats.get("high"),
            "median_comparable_total_cost": round(float(benchmark_total), 2) if benchmark_total else None,
            "median_comparable_price": asking_stats.get("median"),
        })

    confidence_input_values = sold_values if valuation_basis == "sold" else asking_values
    confidence_input_similarity = sold_similarity if valuation_basis == "sold" else asking_similarity
    confidence_input_ages = sold_ages if valuation_basis == "sold" else []
    valuation_confidence = compute_valuation_confidence(
        basis=valuation_basis,
        values=confidence_input_values,
        similarity_scores=confidence_input_similarity,
        ages=confidence_input_ages,
        rejected_count=len(rejected_comps),
    )

    if benchmark_total is None:
        return {
            "success": True,
            "comparable_count": sold_count + asking_count,
            "sold_comparable_count": sold_count,
            "asking_comparable_count": asking_count,
            "summary": "För få tydligt matchande jämförelser för ett marknadsvärde.",
            "price_stats": None,
            "sample_titles": [d["title"] for d in details[:5]],
            "comparable_details": details,
            "valuation_basis": "none",
            "valuation_range": None,
            "rejected_comparable_count": len(rejected_comps),
            "rejected_comparables": rejected_comps[:10],
            "verdict": "För lite data.",
            "confidence": "låg",
            "valuation_confidence_score": valuation_confidence["score"],
            "valuation_confidence_level": valuation_confidence["level"],
            "valuation_confidence_reasons": valuation_confidence["reasons"],
            "valuation_confidence_components": valuation_confidence["components"],
        }

    if current_total_cost < benchmark_total * 0.68:
        verdict = "Tydligt billigt"
    elif current_total_cost < benchmark_total * 0.82:
        verdict = "Ganska billigt"
    elif current_total_cost > benchmark_total * 1.30:
        verdict = "Dyrt"
    else:
        verdict = "Nära marknadspris"

    if valuation_basis == "sold":
        summary = (
            f"Värderingen baseras i första hand på {sold_count} matchande verifierade sålda comps. "
            f"{asking_count} aktiva annonser visas endast som sekundärt marknadsstöd."
        )
    else:
        summary = (
            f"Inga tillräckliga verifierade sålda comps finns i datan. Värderingen använder därför {asking_count} "
            "matchande aktiva annonser konservativt; dessa är begärda priser, inte realiserade försäljningspriser."
        )

    return {
        "success": True,
        "comparable_count": sold_count + asking_count,
        "sold_comparable_count": sold_count,
        "asking_comparable_count": asking_count,
        "summary": summary,
        "price_stats": price_stats,
        "sample_titles": [d["title"] for d in details[:5]],
        "comparable_details": details,
        "valuation_basis": valuation_basis,
        "valuation_range": valuation_range,
        "rejected_comparable_count": len(rejected_comps),
        "rejected_comparables": rejected_comps[:10],
        "verdict": verdict,
        "confidence": confidence,
        "valuation_confidence_score": valuation_confidence["score"],
        "valuation_confidence_level": valuation_confidence["level"],
        "valuation_confidence_reasons": valuation_confidence["reasons"],
        "valuation_confidence_components": valuation_confidence["components"],
    }

