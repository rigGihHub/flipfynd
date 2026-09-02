import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import streamlit as st

try:
    from streamlit_autorefresh import (
        st_autorefresh
    )
except ImportError:
    st_autorefresh = None

from src.card_market_knowledge import detect_market_attention
from src.analysis_cache import (
    build_analysis_signature,
    clear_analysis_cache,
    get_cached_analysis,
    set_cached_analysis,
)

from src.analyzer import (
    analyze_item,
    explain_rank_advantage,
)

from src.loader import (
    load_data,
    load_sold_comps,
)
from src.sold_comp_import import (
    import_sold_comp_rows,
    parse_import_bytes,
    save_sold_comps,
)
from src.sold_comp_collector import collect_sold_comps
from src.visual_detective import analyze_listing_images
from src.visual_identity import build_visual_card_candidates
from src.exact_comp_hunter import hunt_exact_comps
from src.comp_verdict import build_comp_verdict
from src.dynamic_max_bid import build_dynamic_max_bid
from src.detail_evidence_fusion import build_detail_evidence_fusion

from src.pricing import (
    DEFAULT_UNKNOWN_SHIPPING,
    normalize_shipping,
    total_acquisition_cost,
)

from src.tradera_fetcher import (
    CATEGORY_URLS,
    clear_all_loaded_data,
    format_loaded_pages,
    load_fetch_state,
    prune_active_items,
    reconcile_market_state_with_items,
    SMART_MAX_PAGES,
    MAX_ACTIVE_ITEMS_PER_CATEGORY,
    MARKET_BATCH_PAGES,
    get_market_sync_status,
    get_market_coverage_status,
    get_smart_refresh_plan,
    reset_market_sync,
)


st.set_page_config(
    page_title="FlipFynd",
    page_icon="🃏",
    layout="wide",
)


APP_VERSION = "v0.11.6"


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

DATA_PATH = (
    BASE_DIR
    / "tradera_data.json"
)

SOLD_COMPS_PATH = (
    BASE_DIR
    / "data"
    / "sold_comps.json"
)

FETCH_LOG_PATH = (
    BASE_DIR
    / "tradera_fetch_live.log"
)


def read_fetch_log_tail(max_lines=12):
    """Returnera de sista raderna från hämtloggen utan att krascha UI:t."""
    try:
        if not FETCH_LOG_PATH.exists():
            return ""

        lines = FETCH_LOG_PATH.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()

        return "\n".join(lines[-max_lines:])
    except OSError:
        return ""


SPORT_LABELS = {
    "hockey": "Hockey",
    "football": "Fotboll",
}


@st.cache_data(
    show_spinner=False
)

def format_last_fetch_time(value):
    if not value:
        return "Aldrig"
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(value)


def format_freshness_age(age_hours):
    if age_hours is None:
        return "okänd ålder"
    if age_hours < 1:
        minutes = max(1, int(round(age_hours * 60)))
        return f"ca {minutes} min sedan"
    if age_hours < 24:
        return f"ca {int(round(age_hours))} h sedan"
    days = max(1, int(round(age_hours / 24)))
    return f"ca {days} dygn sedan"


def fetch_progress_message():
    state = load_fetch_state()
    run = state.get("active_run", {}) if isinstance(state, dict) else {}
    if run.get("status") != "running":
        return ""

    category = str(run.get("current_category") or "")
    sport_name = "Hockey" if "Hockey" in category else ("Fotboll" if "Fotboll" in category else category)
    page = int(run.get("current_page", 0) or 0)
    seen = int(run.get("category_items_seen", 0) or 0)
    new = int(run.get("category_new_items", 0) or 0)
    completed = run.get("completed_categories", []) or []

    parts = []
    if any("Hockey" in str(x) for x in completed):
        parts.append("Hockey klar ✓")
    if any("Fotboll" in str(x) for x in completed):
        parts.append("Fotboll klar ✓")

    if sport_name:
        if page > 0:
            parts.append(f"Hämtar {sport_name}: sida {page} • {seen} annonser lästa • {new} nya")
        else:
            parts.append(f"Startar {sport_name}…")

    return " • ".join(parts)


def get_dataset_timestamp():
    """Fallback when an older fetch created data before summary metadata existed."""
    try:
        if not DATA_PATH.exists():
            return None
        from datetime import datetime, timezone
        return datetime.fromtimestamp(
            DATA_PATH.stat().st_mtime,
            tz=timezone.utc,
        ).isoformat()
    except OSError:
        return None

@st.cache_data(show_spinner=False)
def get_data(data_version=None):
    # data_version is intentionally part of the cache key. The Tradera fetcher
    # writes page-by-page, so a no-argument cache could otherwise keep showing
    # an old dataset until the subprocess finishes.
    return load_data(str(DATA_PATH))


@st.cache_data(show_spinner=False)
def get_sold_comp_data():
    return load_sold_comps(str(SOLD_COMPS_PATH))


def normalize_text(text):
    if text is None:
        return ""

    text = (
        str(text)
        .lower()
        .replace(
            "-",
            " ",
        )
        .replace(
            "\n",
            " ",
        )
        .replace(
            "\r",
            " ",
        )
    )

    text = text.replace(
        "youngguns",
        "young guns",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def matches_search(
    value,
    search,
):
    search = normalize_text(
        search
    )

    if not search:
        return True

    value = normalize_text(
        value
    )

    if search in value:
        return True

    words = search.split()

    return all(
        word in value
        for word in words
    )


def item_matches_search(
    item,
    search,
):
    return (
        matches_search(
            item.get(
                "titel",
                "",
            ),
            search,
        )
        or matches_search(
            item.get(
                "raw_text",
                "",
            ),
            search,
        )
    )


def infer_item_sport(item):
    source = (
        str(
            item.get(
                "source_category",
                "",
            )
        )
        .lower()
    )

    if (
        "fotboll" in source
        or "football" in source
    ):
        return "football"

    if (
        "hockey" in source
        or "nhl" in source
    ):
        return "hockey"

    return None


def get_seller(item):
    for key in [
        "saljare",
        "säljare",
        "seller",
        "seller_name",
        "username",
    ]:
        value = item.get(
            key
        )

        if (
            value
            and str(
                value
            ).strip()
        ):
            return str(
                value
            ).strip()

    return "Okänd"


def get_data_version():
    parts = []
    for path in (DATA_PATH, SOLD_COMPS_PATH):
        try:
            stat = path.stat()
            parts.append(f"{path.name}:{stat.st_mtime_ns}:{stat.st_size}")
        except FileNotFoundError:
            parts.append(f"{path.name}:missing")
    raw = "|".join(parts)

    return hashlib.md5(
        raw.encode(
            "utf-8"
        )
    ).hexdigest()[:12]


def ensure_state():
    defaults = {
        "fetch_process":
            None,

        "fetch_status":
            "idle",

        "fetch_last_message":
            "",

        "fetch_target_pages":
            0,

        "fetch_start_page":
            1,

        "fetch_category":
            "",

        "results":
            None,

        "debug":
            None,

        "result_cache":
            {},
    }

    for key, value in (
        defaults.items()
    ):
        if key not in (
            st.session_state
        ):
            st.session_state[
                key
            ] = value


def start_fetch(
    category,
    headless,
    mode,
):
    """Starta Tradera-hämtning utan att ett startfel kraschar hela appen."""
    command = [
        sys.executable,
        "fetch_tradera_pages.py",
    ]

    if category == "__all__":
        command.append("--all-categories")
    else:
        command.extend(["--category", category])

    command.extend([
        "--mode",
        mode,
        "--output",
        "tradera_data.json",
    ])

    if not headless:
        command.append("--headed")

    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        log_file = open(
            FETCH_LOG_PATH,
            "w",
            encoding="utf-8",
        )
        process = subprocess.Popen(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(BASE_DIR),
            creationflags=creationflags,
        )
    except Exception as exc:
        try:
            log_file.close()
        except Exception:
            pass
        st.session_state["fetch_process"] = None
        st.session_state["fetch_status"] = "failed"
        st.session_state["fetch_last_message"] = (
            "Tradera-hämtningen kunde inte startas. "
            f"Teknisk orsak: {type(exc).__name__}: {exc}"
        )
        return False

    st.session_state["fetch_process"] = process
    st.session_state["fetch_status"] = "running"
    st.session_state["fetch_category"] = category
    st.session_state["fetch_target_pages"] = 0
    st.session_state["fetch_last_message"] = (
        "Hämtar hockey och fotboll..."
        if category == "__all__"
        else f"Hämtar {category}..."
    )
    return True


def update_fetch_status():
    process = st.session_state.get(
        "fetch_process"
    )

    if process is None:
        return

    return_code = (
        process.poll()
    )

    if return_code is None:
        return

    st.session_state[
        "fetch_process"
    ] = None

    if return_code == 0:
        st.session_state[
            "fetch_status"
        ] = "finished"

        st.session_state[
            "fetch_last_message"
        ] = (
            "Hämtningen är klar."
        )

        get_data.clear()

        st.session_state[
            "result_cache"
        ] = {}

    else:
        st.session_state[
            "fetch_status"
        ] = "failed"

        log_tail = read_fetch_log_tail()

        st.session_state[
            "fetch_last_message"
        ] = (
            "Hämtningen misslyckades. "
            "Öppna hämtloggen nedan för detaljer."
            if log_tail
            else "Hämtningen misslyckades."
        )


def stop_fetch():
    process = (
        st.session_state.get(
            "fetch_process"
        )
    )

    if process:
        try:
            process.terminate()
        except Exception:
            pass

    st.session_state[
        "fetch_process"
    ] = None

    st.session_state[
        "fetch_status"
    ] = "stopped"


def is_numbered(item):
    title = (
        item.get(
            "titel",
            "",
        )
        or ""
    )

    return bool(
        re.search(
            r"(?<!\d)"
            r"(?:"
            r"\d{1,4}/"
            r"\d{1,4}"
            r"|1/1"
            r")"
            r"(?!\d)",
            title,
        )
    )


def is_patch(item):
    text = (
        item.get(
            "titel",
            "",
        )
        or ""
    ).lower()

    return any(
        word in text
        for word in [
            "patch",
            "relic",
            "memorabilia",
            "jersey",
        ]
    )


def is_auto(item):
    text = (
        item.get(
            "titel",
            "",
        )
        or ""
    ).lower()

    return bool(
        re.search(
            r"\b("
            r"auto|"
            r"autograph|"
            r"autograf|"
            r"signed|"
            r"signature"
            r")\b",
            text,
        )
    )


def analyze_data(
    data,
    sport,
    search,
    max_price,
    sale_type,
    full_limit,
    strategy,
    numbered_only,
    patch_only,
    auto_only,
):
    raw_total_items = len(data)
    # Keep interactive analysis bounded even if an older cloud runtime still
    # contains a very large crawl. This is a CPU guard, not a ranking signal.
    data = prune_active_items(data, max_per_category=MAX_ACTIVE_ITEMS_PER_CATEGORY)
    debug = {
        "total_items": raw_total_items,
        "performance_items": len(data),
        "after_sport": 0,
        "valid_price": 0,
        "within_budget": 0,
        "after_search": 0,
        "after_sale_type": 0,
        "after_feature_filters": 0,
        "missing_or_invalid_price": 0,
        "over_budget": 0,
        "search_miss": 0,
        "sale_type_miss": 0,
        "feature_filter_miss": 0,
        "fast_candidates": 0,
        "full_analysis": 0,
        "cache_hits": 0,
        "final_results": 0,
    }

    candidates = []

    data_version = (
        get_data_version()
    )

    # Comps ska alltid komma från samma sport som objektet som analyseras.
    sport_items = [
        item for item in data
        if isinstance(item, dict)
        and (infer_item_sport(item) in {None, sport})
    ]
    sold_comp_items = [
        item for item in get_sold_comp_data()
        if isinstance(item, dict)
        and (infer_item_sport(item) in {None, sport})
    ]
    market_items = sport_items + sold_comp_items

    # Seller presentation context: only descriptive metadata. It must never
    # create a valuation. A high generic-title ratio can reveal listings that
    # informed buyers may find more easily than the wider market.
    seller_rows = {}
    for row in sport_items:
        seller = get_seller(row)
        if seller == "Okänd":
            continue
        title = str(row.get("titel") or row.get("title") or "").strip().lower()
        generic = (len(title) < 28 or title in {"hockeykort", "fotbollskort", "samlarkort"}
                   or title.startswith("hockeykort ") or title.startswith("fotbollskort "))
        bucket = seller_rows.setdefault(seller, {"count": 0, "generic": 0})
        bucket["count"] += 1
        bucket["generic"] += int(generic)
    for row in sport_items:
        seller = get_seller(row)
        stats = seller_rows.get(seller)
        if stats:
            row["seller_listing_count"] = stats["count"]
            row["seller_generic_title_ratio"] = stats["generic"] / max(1, stats["count"])

    for item in data:
        if not isinstance(
            item,
            dict,
        ):
            continue

        item_sport = (
            infer_item_sport(
                item
            )
        )

        if (
            item_sport
            and item_sport
            != sport
        ):
            continue

        debug[
            "after_sport"
        ] += 1

        price = item.get(
            "pris"
        )

        if (
            not isinstance(price, (int, float))
            or price <= 0
        ):
            debug["missing_or_invalid_price"] += 1
            continue

        debug["valid_price"] += 1

        total_cost = total_acquisition_cost(
            price,
            item.get("frakt"),
        )

        if total_cost is None or total_cost > max_price:
            debug["over_budget"] += 1
            continue

        debug["within_budget"] += 1

        if not item_matches_search(item, search):
            debug["search_miss"] += 1
            continue

        debug["after_search"] += 1

        fast = analyze_item(
            item,
            mode="fast",
            strategy_mode=
                strategy,
            sport=sport,
        )

        if (
            sale_type == "Endast auktioner"
            and fast.get("sale_type") != "Auktion"
        ) or (
            sale_type == "Endast Köp nu"
            and fast.get("sale_type") != "Köp nu"
        ):
            debug["sale_type_miss"] += 1
            continue

        debug["after_sale_type"] += 1

        if (
            (numbered_only and not is_numbered(item))
            or (patch_only and not is_patch(item))
            or (auto_only and not is_auto(item))
        ):
            debug["feature_filter_miss"] += 1
            continue

        debug["after_feature_filters"] += 1

        attention = detect_market_attention(
            f"{item.get('titel', '')} {item.get('raw_text', '') or ''}",
            sport=sport,
        )
        candidates.append(
            (
                item,
                fast,
                attention,
            )
        )

    # Full-analysis preselection may prioritize known scarce/chase structures so
    # they are not missed by the cheap fast pass. This boost does NOT change
    # market value, profit, max bid or the final result ranking.
    candidates.sort(
        key=lambda value: (
            value[1].get("rank_score", 0)
            + value[2].get("score", 0)
            + min(12, int(value[1].get("player_card_demand_preselection_boost", 0) or 0)),
            value[1].get("rank_score", 0),
            value[1].get("player_card_demand_review_priority_score", 0),
            value[1].get("player_market_score", 0),
        ),
        reverse=True,
    )

    debug[
        "fast_candidates"
    ] = len(
        candidates
    )

    results = []

    for (
        original,
        fast,
        _attention,
    ) in candidates[
        :full_limit
    ]:
        signature = (
            build_analysis_signature(
                original,
                data_size=len(
                    data
                ),
                mode=(
                    f"{sport}_"
                    f"{strategy}_"
                    f"{data_version}"
                ),
            )
        )

        cached = (
            get_cached_analysis(
                signature
            )
        )

        if cached:
            full = cached

            debug[
                "cache_hits"
            ] += 1

        else:
            full = analyze_item(
                original,
                all_items=market_items,
                mode="full",
                strategy_mode=
                    strategy,
                sport=sport,
            )

            set_cached_analysis(
                signature,
                full,
            )

            debug[
                "full_analysis"
            ] += 1

        results.append(
            full
        )

    for (
        _,
        fast,
        _attention,
    ) in candidates[
        full_limit:
    ]:
        results.append(
            fast
        )

    results.sort(
        key=lambda item: (
            item.get(
                "rank_score",
                0,
            ),
            item.get(
                "player_market_score",
                0,
            ),
            item.get(
                "risk_adjusted_profit",
                0,
            ),
        ),
        reverse=True,
    )

    debug[
        "final_results"
    ] = len(
        results
    )

    return (
        results,
        debug,
    )


ensure_state()
update_fetch_status()

if st.session_state.get("fetch_status") == "running":
    # Data is persisted page-by-page during a crawl; refresh the cached dataset
    # so counts and newly fetched sport data become visible immediately.
    get_data.clear()


if (
    st.session_state[
        "fetch_status"
    ]
    == "running"
    and st_autorefresh
):
    st_autorefresh(
        interval=3000,
        key="fetch_refresh",
    )


st.markdown(
    """
    <style>
    :root {
        --ff-ink: #16171a;
        --ff-paper: #f4ead7;
        --ff-cream: #fff6e5;
        --ff-orange: #e86f3b;
        --ff-teal: #2f8f83;
        --ff-gold: #e1ad4d;
        --ff-panel: #202329;
        --ff-panel-2: #292d34;
        --ff-line: rgba(244, 234, 215, 0.20);
    }
    .stApp {
        background:
            linear-gradient(rgba(255,255,255,.018) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,.014) 1px, transparent 1px),
            #111317;
        background-size: 24px 24px;
    }
    .block-container {
        max-width: 1500px;
        padding-top: 1.5rem;
    }
    .ff-hero {
        position: relative;
        overflow: hidden;
        border: 2px solid var(--ff-paper);
        border-radius: 6px;
        padding: 1.05rem 1.25rem 1rem 1.25rem;
        margin: 0.1rem 0 0.75rem 0;
        background: linear-gradient(135deg, #1b1d22 0%, #22262b 100%);
        box-shadow: 7px 7px 0 rgba(232,111,59,.34);
    }
    .ff-hero:before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 7px;
        background: linear-gradient(90deg, var(--ff-orange) 0 35%, var(--ff-gold) 35% 58%, var(--ff-teal) 58% 100%);
    }
    .ff-hero h1 {
        margin: 0.15rem 0 0.2rem 0;
        color: var(--ff-cream);
        letter-spacing: .02em;
        font-size: clamp(2rem, 4vw, 3.35rem);
        line-height: 1;
        text-shadow: 3px 3px 0 rgba(232,111,59,.38);
    }
    .ff-kicker {
        color: var(--ff-gold);
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: .77rem;
        font-weight: 800;
        letter-spacing: .14em;
        text-transform: uppercase;
        margin-bottom: .35rem;
    }
    .ff-muted {
        color: #c9c1b5;
        font-size: 0.94rem;
        max-width: 850px;
    }
    .ff-status-strip {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: .78rem;
        letter-spacing: .04em;
        color: #d6cdbf;
        margin: .2rem 0 .8rem 0;
    }
    h1, h2, h3 {
        letter-spacing: -.015em;
    }
    div[data-testid="stForm"], div[data-testid="stExpander"] {
        border-color: var(--ff-line);
        border-radius: 6px;
    }
    div[data-testid="stMetric"] {
        border: 1px solid var(--ff-line) !important;
        border-radius: 5px !important;
        padding: 0.6rem 0.7rem !important;
        background: rgba(255,246,229,.025);
        box-shadow: 3px 3px 0 rgba(47,143,131,.10);
    }
    div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button {
        border-radius: 4px;
        border-width: 1px;
        font-weight: 760;
        letter-spacing: .015em;
        min-height: 2.65rem;
    }
    div[data-testid="stButton"] > button[kind="primary"] {
        background: var(--ff-orange);
        border-color: #ffad73;
        color: #16171a;
        box-shadow: 4px 4px 0 #7d3c27;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background: #f47f49;
        border-color: var(--ff-cream);
        transform: translate(-1px,-1px);
        box-shadow: 5px 5px 0 #7d3c27;
    }
    .ff-decision {
        font-size: 1.05rem;
        font-weight: 750;
        margin-bottom: 0.15rem;
    }
    .ff-card-title {
        font-size: 1.2rem;
        font-weight: 700;
        line-height: 1.3;
        margin-bottom: 0.45rem;
    }

    .ff-result-head {
        position: relative;
        border: 2px solid var(--ff-paper);
        border-bottom: 5px solid var(--ff-orange);
        border-radius: 7px;
        padding: .85rem 1rem .8rem 1rem;
        margin: .1rem 0 .65rem 0;
        background:
            repeating-linear-gradient(135deg, rgba(255,255,255,.025) 0 8px, transparent 8px 16px),
            linear-gradient(135deg, #22262c, #191c20);
        box-shadow: 6px 6px 0 rgba(47,143,131,.20);
    }
    .ff-result-topline { display:flex; gap:.55rem; align-items:center; flex-wrap:wrap; margin-bottom:.45rem; }
    .ff-rank-chip, .ff-decision-chip, .ff-score-chip {
        display:inline-block; padding:.18rem .46rem; border:1px solid var(--ff-paper); border-radius:3px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size:.73rem; font-weight:900; letter-spacing:.06em; text-transform:uppercase;
    }
    .ff-rank-chip { background:var(--ff-gold); color:#171717; border-color:#ffd984; }
    .ff-score-chip { background:var(--ff-teal); color:#081917; border-color:#74d2c7; }
    .ff-decision-chip.buy { background:#6ecb8b; color:#102015; border-color:#b5f0c6; }
    .ff-decision-chip.watch { background:#f0c75e; color:#251f0a; border-color:#ffe7a3; }
    .ff-decision-chip.skip { background:#d66d61; color:#26100e; border-color:#f0a39a; }
    .ff-result-title { color:var(--ff-cream); font-weight:850; font-size:1.22rem; line-height:1.25; margin:.15rem 0 .25rem 0; }
    .ff-result-sub { color:#c9c1b5; font-size:.82rem; font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; }
    .ff-quick-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.45rem; margin:.65rem 0 .5rem 0; }
    .ff-quick-cell { border:1px solid var(--ff-line); background:rgba(255,246,229,.035); padding:.5rem .55rem; min-height:62px; }
    .ff-quick-label { color:#aaa298; font-size:.67rem; text-transform:uppercase; letter-spacing:.08em; }
    .ff-quick-value { color:var(--ff-cream); font-size:1rem; font-weight:850; margin-top:.08rem; }
    .ff-retro-rule { height:5px; margin:.6rem 0 .15rem 0; background:linear-gradient(90deg,var(--ff-orange) 0 38%,var(--ff-gold) 38% 66%,var(--ff-teal) 66% 100%); }
    @media (max-width: 800px) {
        .ff-quick-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
        .ff-result-title { font-size:1.08rem; }
    }

    .ff-data-card {
        border: 2px solid var(--ff-gold);
        border-radius: 6px;
        padding: 1rem 1.1rem 0.45rem 1.1rem;
        margin: 0.55rem 0 1rem 0;
        background: linear-gradient(135deg, rgba(225,173,77,.10), rgba(47,143,131,.07));
        box-shadow: 5px 5px 0 rgba(225,173,77,.14);
    }
    .ff-data-card h3 {
        margin: 0 0 0.25rem 0;
    }
    .ff-data-card p {
        margin: 0 0 0.65rem 0;
        color: #d1c8bb;
    }
    @media (max-width: 640px) {
        .ff-card-title { font-size: 1.05rem; }
        .ff-decision { font-size: 1rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="ff-hero">
      <div class="ff-kicker">COLLECTOR MARKET SCANNER // EST. 2026</div>
      <h1>🃏 FLIPFYND</h1>
      <div class="ff-muted">Hitta samlarkort med potential för vidareförsäljning – rankade efter pris, efterfrågan, säljsannolikhet och möjlig vinst.</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(f'<div class="ff-status-strip">{APP_VERSION} &nbsp;•&nbsp; HOCKEY + FOTBOLL &nbsp;•&nbsp; TRADERA SCANNER</div>', unsafe_allow_html=True)

if st.session_state.get("fetch_last_message"):
    message = st.session_state["fetch_last_message"]
    if st.session_state.get("fetch_status") == "finished":
        st.success(message)
    elif st.session_state.get("fetch_status") == "running":
        live_message = fetch_progress_message()
        st.info(live_message or message)

data = get_data(get_data_version())
if not isinstance(data, list):
    data = []

# Repair legacy market coverage only when the saved page-state is clearly
# inconsistent with the category ids in the listings themselves.
try:
    repaired_categories = reconcile_market_state_with_items(data)
except Exception:
    repaired_categories = []

_current_dataset_version = get_data_version()
_previous_result_version = st.session_state.get("results_data_version")
if (
    st.session_state.get("results") is not None
    and _previous_result_version
    and _previous_result_version != _current_dataset_version
):
    st.session_state["results"] = None
    st.session_state["debug"] = None
    st.session_state["results_stale_notice"] = True

st.subheader("Hitta fynd")
if repaired_categories:
    st.info(
        "🧭 Marknadstäckningen har rättats för "
        + ", ".join(repaired_categories)
        + ". Gammal sidstatus stämde inte med annonslänkarna och har därför byggts om från verifierad data."
    )
if st.session_state.pop("results_stale_notice", False):
    st.caption("🔄 Annonsdata ändrades efter din förra sökning. Det gamla sökresultatet rensades så att du inte ser en inaktuell nolla.")
_fetch_state_summary = load_fetch_state()
_last_values = [
    info.get("last_fetch_at")
    for info in _fetch_state_summary.get("categories", {}).values()
    if info.get("last_fetch_at")
]
if _last_values:
    _latest_fetch = format_last_fetch_time(max(_last_values))
    _latest_label = "senast hämtat"
else:
    _dataset_timestamp = get_dataset_timestamp()
    _latest_fetch = format_last_fetch_time(_dataset_timestamp) if _dataset_timestamp else "Aldrig"
    _latest_label = "data senast ändrad" if _dataset_timestamp else "senast hämtat"

_sport_counts = {"hockey": 0, "football": 0, "unknown": 0}
for _item in data:
    _sport = infer_item_sport(_item)
    if _sport in ("hockey", "football"):
        _sport_counts[_sport] += 1
    else:
        _sport_counts["unknown"] += 1

_count_parts = [
    f"{_sport_counts['hockey']:,} hockey",
    f"{_sport_counts['football']:,} fotboll",
]
if _sport_counts["unknown"]:
    _count_parts.append(f"{_sport_counts['unknown']:,} okategoriserade")

st.caption(
    (
        f"{len(data):,} annonser totalt • "
        + " • ".join(_count_parts)
        + f" • {_latest_label} {_latest_fetch}"
    ).replace(",", " ")
)

if len(data) > MAX_ACTIVE_ITEMS_PER_CATEGORY * 2:
    st.info(
        "⚡ Prestandaskydd aktivt: FlipFynd analyserar den senaste begränsade delen av marknaden "
        "i stället för att CPU-analysera hela den äldre masshämtningen på en gång."
    )

if _sport_counts["hockey"] == 0 and _sport_counts["football"] > 100:
    st.warning(
        "🏒 Hockeydata saknas i nuvarande dataset. Nästa smarta uppdatering validerar sport direkt "
        "mot Traderas kategori-id och stoppar fel sport från att blandas in."
    )

_detail_enriched_count = sum(
    1 for _item in data
    if _item.get("detail_enrichment_status") == "ok"
)
if _detail_enriched_count:
    st.caption(
        f"🔍 {_detail_enriched_count} annonser har berikats från själva Tradera-annonsen "
        "med extra beskrivning, bilder och metadata när det varit möjligt."
    )

_fetch_status = st.session_state.get("fetch_status", "idle")
_has_data = len(data) > 0

if not _has_data:
    st.markdown(
        """
        <div class="ff-data-card">
          <h3>📥 Börja här – hämta annonser från Tradera</h3>
          <p>FlipFynd har inga annonser inlästa ännu. Hämta hockey och fotboll först; därefter kan appen söka och ranka fynd.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if _fetch_status == "running":
        st.info(fetch_progress_message() or "Hämtningen pågår… Nya annonser visas automatiskt när de sparas.")
        if st.button("⏹ Avbryt hämtning", use_container_width=True, key="top_stop_fetch"):
            stop_fetch()
            st.rerun()
    else:
        primary_label = (
            "🔄 Försök hämta annonser igen"
            if _fetch_status == "failed"
            else "🔄 Hämta hockey + fotboll från Tradera"
        )
        if st.button(
            primary_label,
            type="primary",
            use_container_width=True,
            key="top_fetch_all",
        ):
            start_fetch("__all__", True, "incremental")
            st.rerun()
        st.caption("Smart uppdatering används automatiskt. Du behöver inte välja sidor eller göra några tekniska inställningar.")

    if _fetch_status == "failed":
        st.error(
            st.session_state.get("fetch_last_message")
            or "Tradera-hämtningen misslyckades. Försök igen eller öppna de tekniska detaljerna nedan."
        )
        log_tail = read_fetch_log_tail()
        if log_tail:
            with st.expander("Tekniska detaljer – använd detta om felet återkommer"):
                st.code(log_tail, language="text")
else:
    top_left, top_right = st.columns([3, 1])
    with top_left:
        st.caption("✅ Annonsdata finns inläst. Du kan söka fynd direkt eller göra en snabb kontroll av de nyaste annonserna.")
        st.caption("**🔄 Uppdatera annonser** = börjar från sida 1 och letar efter nya/förändrade annonser. Den är snabb och är knappen du normalt använder varje dag.")
    with top_right:
        if st.button(
            "🔄 Uppdatera annonser",
            use_container_width=True,
            disabled=_fetch_status == "running",
            key="top_refresh_data",
            help="Snabb uppdatering av de nyaste Tradera-sidorna. Den fortsätter inte den djupa fullmarknadsläsningen.",
        ):
            start_fetch("__all__", True, "incremental")
            st.rerun()

    coverage_h = get_market_coverage_status("Hockey - NHL")
    coverage_f = get_market_coverage_status("Fotboll")
    refresh_h = get_smart_refresh_plan("Hockey - NHL")
    refresh_f = get_smart_refresh_plan("Fotboll")
    st.markdown(
        '<div class="ff-data-card"><h3>📡 MARKNADSSCANNER</h3>'
        '<p>Bygg upp hela Tradera-marknaden i små omgångar. Den här scannern är separat från den snabba dagliga uppdateringen.</p></div>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    for col, icon, label, coverage in [
        (c1, "🏒", "Hockey", coverage_h),
        (c2, "⚽", "Fotboll", coverage_f),
    ]:
        with col:
            st.markdown(f"**{icon} {label}**")
            st.write(coverage["coverage_label"])
            if coverage["complete"]:
                st.caption(f"✅ Full täckning • {coverage['loaded_page_count']} sidor inlästa")
            else:
                st.caption(f"Nästa omgång börjar på sida {coverage['next_page']} • {coverage['loaded_page_count']} sidor sparade")
            freshness_icon = "🟢" if coverage["freshness"] == "fresh" else ("🟡" if coverage["freshness"] == "aging" else "🔴" if coverage["freshness"] == "stale" else "⚪")
            st.caption(f"{freshness_icon} {coverage['freshness_label']} • {format_freshness_age(coverage['age_hours'])}")
            if coverage["missing_pages"]:
                preview = ", ".join(str(p) for p in coverage["missing_pages"][:8])
                more = " …" if len(coverage["missing_pages"]) > 8 else ""
                st.caption(f"⚠️ Luckor i sidtäckningen: {preview}{more}")

    if not (coverage_h["complete"] and coverage_f["complete"]):
        action_left, action_right = st.columns([3, 1])
        with action_left:
            st.caption(
                f"**▶ Läs nästa omgång** = fortsätter där fullmarknadsscannern slutade och läser högst {MARKET_BATCH_PAGES} nya sidor per sport. "
                "Använd den flera gånger tills respektive sport visar **Hela marknaden inläst**. Redan sparade annonser behålls."
            )
        with action_right:
            if st.button(
                "▶ Läs nästa omgång",
                use_container_width=True,
                disabled=_fetch_status == "running",
                key="top_market_batch",
                help="Fortsätt fullmarknadsläsningen från nästa ej lästa sida. Detta är tyngre än en vanlig uppdatering.",
            ):
                start_fetch("__all__", True, "market_batch")
                st.rerun()
    else:
        st.success("✅ Fullmarknadsscannern har nått slutet för både hockey och fotboll. Använd normalt bara Uppdatera annonser för att hålla de nyaste sidorna färska.")

    st.caption(
        f"Alla inlästa annonser sparas. Själva fyndanalysen arbetar fortfarande med högst {MAX_ACTIVE_ITEMS_PER_CATEGORY} nyare annonser per sport åt gången för att hålla appen snabb."
    )

    st.markdown(
        '<div class="ff-data-card"><h3>⏱ SMART REFRESH</h3>'
        '<p>FlipFynd prioriterar automatiskt vilka redan inlästa sidor som behöver läsas om. Nya sidor kontrolleras oftare, djupa äldre sidor mer sällan.</p></div>',
        unsafe_allow_html=True,
    )
    r1, r2 = st.columns(2)
    for col, icon, label, plan in [
        (r1, "🏒", "Hockey", refresh_h),
        (r2, "⚽", "Fotboll", refresh_f),
    ]:
        with col:
            if plan.get("due"):
                st.markdown(f"**{icon} {label}: behöver uppdateras**")
                st.caption(f"Sida {plan['start_page']}–{plan['end_page']} • {plan.get('reason','')}")
            else:
                st.markdown(f"**{icon} {label}: tillräckligt färsk**")
                wait = plan.get("next_due_hours")
                if wait is not None:
                    st.caption(f"Nästa område blir aktuellt om cirka {max(0, round(wait, 1))} timmar.")
                else:
                    st.caption("Ingen ny uppdatering behövs just nu.")

    st.caption(
        "**⚡ Uppdatera det som behövs** = läser bara ett litet sidblock som faktiskt blivit gammalt. "
        "Sida 1–5 kontrolleras ungefär var 2:e timme, 6–20 var 8:e timme, 21–60 dagligen och djupare sidor ungefär var tredje dag. "
        "Detta är CPU-snålast när hela marknaden redan är inläst stegvis."
    )
    if st.button(
        "⚡ Uppdatera det som behövs",
        use_container_width=True,
        disabled=_fetch_status == "running" or not (refresh_h.get("due") or refresh_f.get("due")),
        key="top_smart_refresh",
        help="Uppdaterar bara det äldsta prioriterade sidblocket per sport. Den läser inte om hela marknaden.",
    ):
        start_fetch("__all__", True, "scheduled_refresh")
        st.rerun()

def render_search_pipeline(debug, sport_label, max_price, search):
    """Explain where listings disappear without guessing about the market."""
    if not isinstance(debug, dict):
        return
    stages = [
        ("Dataset", int(debug.get("total_items", 0) or 0)),
        ("Efter prestandaskydd", int(debug.get("performance_items", 0) or 0)),
        (f"{sport_label}", int(debug.get("after_sport", 0) or 0)),
        ("Har giltigt pris", int(debug.get("valid_price", 0) or 0)),
        (f"Inom budget {int(max_price)} kr", int(debug.get("within_budget", 0) or 0)),
        ("Matchar sökning", int(debug.get("after_search", 0) or 0)),
        ("Rätt annonsform", int(debug.get("after_sale_type", 0) or 0)),
        ("Efter specialfilter", int(debug.get("after_feature_filters", 0) or 0)),
        ("Analyserade kandidater", int(debug.get("final_results", 0) or 0)),
    ]
    st.markdown("### 🔎 Sållning – var försvinner annonserna?")
    st.caption("Varje steg visar hur många annonser som återstår. Då ser du om problemet är data, budget, sökning eller ett filter.")
    cols = st.columns(3)
    for idx, (label, value) in enumerate(stages):
        cols[idx % 3].metric(label, value)

    sport_count = int(debug.get("after_sport", 0) or 0)
    if sport_count and int(debug.get("valid_price", 0) or 0) == 0:
        st.error("Alla annonser för vald sport saknar ett användbart pris. Det pekar på ett inläsnings-/parserfel, inte på dina sökfilter.")
    elif int(debug.get("valid_price", 0) or 0) and int(debug.get("within_budget", 0) or 0) == 0:
        st.warning("Alla annonser med giltigt pris ligger över vald totalbudget. Höj budgeten för att se kandidater.")
    elif int(debug.get("within_budget", 0) or 0) and int(debug.get("after_search", 0) or 0) == 0 and str(search or "").strip():
        st.warning("Budgeten släpper igenom annonser, men ingen matchar söktexten. Prova kortare eller tom sökning.")
    elif int(debug.get("after_search", 0) or 0) and int(debug.get("after_sale_type", 0) or 0) == 0:
        st.warning("Annonsform-filtret sorterar bort allt. Välj Alla för att kontrollera marknaden.")
    elif int(debug.get("after_sale_type", 0) or 0) and int(debug.get("after_feature_filters", 0) or 0) == 0:
        st.warning("Ett specialfilter – numrerat, patch/relic eller autograf – sorterar bort alla annonser.")


with st.form("analysis_form"):
    p1, p2 = st.columns(2)

    with p1:
        sport_label = st.selectbox(
            "Sport",
            ["Hockey", "Fotboll"],
        )
        sport = "hockey" if sport_label == "Hockey" else "football"

    with p2:
        max_price = st.number_input(
            "Budget – max totalpris inkl. frakt",
            min_value=0,
            value=1000,
            step=50,
            help="Annonser vars pris + frakt överstiger budgeten sorteras bort.",
        )

    p3, p4 = st.columns(2)

    with p3:
        strategy_label = st.selectbox(
            "Strategi",
            [
                "Snabb flip",
                "Störst vinstpotential",
                "Bästa kortet",
            ],
            help="Snabb flip prioriterar lättsålda kort. Störst vinstpotential väger premiumegenskaper högre. Bästa kortet prioriterar kortkvalitet och spelare.",
        )

    with p4:
        search = st.text_input(
            "Sök spelare, set eller kort",
            value="",
            placeholder="T.ex. Bedard, Young Guns, Messi…",
        )

    strategy_map = {
        "Snabb flip": "quick_flip",
        "Störst vinstpotential": "premium_flip",
        "Bästa kortet": "kort",
    }
    strategy = strategy_map[strategy_label]

    with st.expander("Avancerade filter"):
        a1, a2 = st.columns(2)
        with a1:
            sale_type = st.selectbox(
                "Annonsform",
                ["Alla", "Endast auktioner", "Endast Köp nu"],
            )
            minimum_confidence = st.slider(
                "Minsta analyssäkerhet",
                0.0,
                1.0,
                0.0,
                0.05,
            )

        with a2:
            show_count = st.number_input(
                "Antal fynd att visa",
                min_value=1,
                max_value=100,
                value=20,
            )
            show_skip = st.checkbox(
                "Visa även svaga kandidater",
                value=True,
                help="På som standard så att FlipFynd alltid visar de bäst rankade korten, även när inget når köpgränsen.",
            )

        f1, f2, f3 = st.columns(3)
        with f1:
            numbered_only = st.checkbox("Endast numrerade", value=False)
        with f2:
            patch_only = st.checkbox("Endast patch/relic", value=False)
        with f3:
            auto_only = st.checkbox("Endast autograf", value=False)

    # Intern prestandaparameter: användaren ska inte behöva förstå den.
    full_limit = 12

    run = st.form_submit_button(
        "🔎 Hitta fynd" if _has_data else "📥 Hämta annonser först",
        type="primary",
        use_container_width=True,
        disabled=not _has_data,
    )


if run:
    with st.spinner(f"Analyserar {sport_label.lower()} och rankar de bästa fynden…"):
        results, debug = analyze_data(
            data=data,
            sport=sport,
            search=search,
            max_price=max_price,
            sale_type=sale_type,
            full_limit=full_limit,
            strategy=strategy,
            numbered_only=numbered_only,
            patch_only=patch_only,
            auto_only=auto_only,
        )

    st.session_state["results"] = results
    st.session_state["debug"] = debug
    st.session_state["results_data_version"] = get_data_version()


if st.session_state.get("results") is not None:
    filtered = []

    for item in st.session_state["results"]:
        if item.get("confidence", 0) < minimum_confidence:
            continue

        if not show_skip and item.get("beslut") == "SKIP":
            continue

        filtered.append(item)

    visible = filtered[: int(show_count)]

    st.divider()
    non_skip_count = sum(1 for item in st.session_state["results"] if item.get("beslut") != "SKIP")
    if non_skip_count > 0:
        st.subheader(f"Bästa fynden ({len(visible)})")
    else:
        st.subheader(f"Bästa kandidaterna ({len(visible)})")
        if visible:
            st.info(
                "Inget kort når FlipFynds köpgräns just nu. De bäst rankade kandidaterna visas ändå så att du kan bedöma marknaden."
            )

    if not visible:
        if not data:
            st.warning(
                "Inga annonser är inlästa ännu. Hämta annonser från Tradera först – dina filter är inte problemet."
            )
        elif st.session_state.get("debug", {}).get("final_results", 0) == 0:
            st.warning(
                "FlipFynd hittade inga analyserbara kandidater. Öppna sållningen nedan – den visar exakt vilket steg som tar bort annonserna."
            )
        else:
            st.info(
                "Annonser passerade grundfiltren men inga syns efter visningsfiltren. Kontrollera analyssäkerhet och 'Visa även svaga kandidater'."
            )

    with st.expander("🔎 Visa varför annonser sorterades bort", expanded=not bool(visible)):
        render_search_pipeline(
            st.session_state.get("debug", {}),
            sport_label=sport_label,
            max_price=max_price,
            search=search,
        )

    # Opportunity Radar reduces the analysed market to a short action queue.
    radar_groups = {name: [] for name in ("AGERA NU", "BEVAKA", "UNDERSÖK", "IGNORERA")}
    for candidate in filtered:
        radar_groups.setdefault(candidate.get("opportunity_action", "IGNORERA"), []).append(candidate)
    for group in radar_groups.values():
        group.sort(key=lambda x: x.get("opportunity_priority_score", 0), reverse=True)

    actionable = radar_groups["AGERA NU"] + radar_groups["BEVAKA"] + radar_groups["UNDERSÖK"]
    actionable.sort(key=lambda x: x.get("opportunity_priority_score", 0), reverse=True)
    if actionable:
        st.subheader("📡 Opportunity Radar")
        st.caption("FlipFynd kokar ned marknaden till vad som är värt din tid just nu. Radarn ändrar inte värdering, maxbud eller köpbeslut.")
        cols = st.columns(3)
        cols[0].metric("🚨 Agera nu", len(radar_groups["AGERA NU"]))
        cols[1].metric("👀 Bevaka", len(radar_groups["BEVAKA"]))
        cols[2].metric("🔎 Undersök", len(radar_groups["UNDERSÖK"]))
        for candidate in actionable[:5]:
            action = candidate.get("opportunity_action")
            st.write(f"**{action} · {candidate.get('titel', 'Okänd annons')}**")
            st.caption(
                f"Prioritet {candidate.get('opportunity_priority_score', 0):.0f}/100 · "
                f"Fyndpoäng {candidate.get('deal_score', 0):.0f}/100 · "
                f"Risk {candidate.get('risk_score', 0):.0f}/100"
            )
            if candidate.get("opportunity_reasons"):
                st.caption(" • ".join(candidate.get("opportunity_reasons")[:2]))
            if candidate.get("lank"):
                st.markdown(f"[Öppna på Tradera]({candidate.get('lank')})")
        st.divider()

    visual_candidates = [
        x for x in filtered
        if x.get("visual_verification_required") and x.get("visual_image_count", 0) > 0
    ]
    visual_candidates.sort(
        key=lambda x: (x.get("visual_edge_score", 0), x.get("opportunity_priority_score", 0)), reverse=True
    )
    if visual_candidates:
        with st.expander(f"👁️ Visual Edge ({len(visual_candidates)})", expanded=False):
            st.caption(
                "Här prioriteras annonser där bilderna kan vara extra viktiga för att verifiera exakt kort. "
                "v0.9.1 kan på begäran låta en bildmodell skapa försiktiga hypoteser om synliga kortdetaljer. Hypoteserna påverkar aldrig värdering eller maxbud automatiskt."
            )
            for candidate in visual_candidates[:8]:
                cols = st.columns([1, 3])
                image_urls = candidate.get("visual_image_urls") or []
                with cols[0]:
                    if image_urls:
                        st.image(image_urls[0], use_container_width=True)
                with cols[1]:
                    st.write(
                        f"**{candidate.get('titel', 'Okänd annons')}** · "
                        f"Bildprioritet {candidate.get('visual_edge_score', 0):.0f}/100"
                    )
                    if candidate.get("visual_edge_reasons"):
                        st.caption(" • ".join(candidate.get("visual_edge_reasons")[:3]))
                    if candidate.get("lank"):
                        st.markdown(f"[Öppna på Tradera]({candidate.get('lank')})")
                    detective_key = "visual_detective_" + str(candidate.get("lank") or candidate.get("titel") or "")
                    if st.button("🔬 Analysera bilden", key="btn_" + detective_key):
                        with st.spinner("Granskar synliga kortdetaljer …"):
                            st.session_state[detective_key] = analyze_listing_images({
                                "titel": candidate.get("titel", ""),
                                "raw_text": candidate.get("raw_text", ""),
                                "image_urls": candidate.get("visual_image_urls", []),
                            })
                    detective = st.session_state.get(detective_key)
                    if detective:
                        if not detective.get("success"):
                            st.warning(detective.get("error", "Bildanalysen kunde inte genomföras."))
                        else:
                            comp = detective.get("comparison", {})
                            findings = detective.get("findings", {})
                            st.markdown(f"**Visual Card Detective:** {comp.get('status', 'Granskad')} · säkerhet {comp.get('confidence', 0):.0f}/100")
                            for discovery in comp.get("discoveries", [])[:4]:
                                st.caption("🔎 " + discovery)
                            for conflict in comp.get("conflicts", [])[:3]:
                                st.caption("⚠️ " + conflict)

                            visual_fusion = build_detail_evidence_fusion(
                                {
                                    "titel": candidate.get("titel", ""),
                                    "raw_text": candidate.get("raw_text", ""),
                                    "full_description": candidate.get("full_description", ""),
                                },
                                visual_findings=findings,
                            )
                            st.markdown(
                                f"**🧩 Evidence Fusion inkl. bild:** {visual_fusion.get('status')} · "
                                f"{visual_fusion.get('score', 0)}/100"
                            )
                            if visual_fusion.get("corroborated_fields"):
                                st.caption(
                                    "Flerkällestöd: " + " • ".join(visual_fusion.get("corroborated_fields")[:5])
                                )
                            for discovery in visual_fusion.get("discoveries", [])[:3]:
                                st.caption("➕ " + discovery)
                            for conflict in visual_fusion.get("conflicts", [])[:3]:
                                st.caption("⛔ " + conflict)

                            clues = findings.get("visual_clues", [])
                            if clues:
                                st.caption("Synliga ledtrådar: " + " • ".join(clues[:4]))
                            uncertainties = findings.get("uncertainties", [])
                            if uncertainties:
                                st.caption("Osäkerheter: " + " • ".join(uncertainties[:3]))
                            identity = build_visual_card_candidates(
                                findings,
                                listing_title=candidate.get("titel", ""),
                                listing_raw_text=candidate.get("raw_text", ""),
                                observed_records=get_sold_comp_data(),
                            )
                            st.markdown(f"**🎯 Kortkandidater:** {identity.get('status', 'Otillräckligt underlag')}")
                            for idx, card_candidate in enumerate(identity.get("candidates", [])[:3], start=1):
                                badge = "✅" if card_candidate.get("verified_identity") else "🧩"
                                st.caption(
                                    f"{badge} {idx}. {card_candidate.get('label')} · "
                                    f"match {card_candidate.get('match_score', 0):.0f}/100 · {card_candidate.get('status')}"
                                )
                                evidence = card_candidate.get("evidence") or []
                                if evidence:
                                    st.caption("Stöd: " + " • ".join(evidence[:5]))
                            for blocker in identity.get("blockers", [])[:3]:
                                st.caption("⛔ " + blocker)
                            verified_candidates = [c for c in identity.get("candidates", []) if c.get("verified_identity")]
                            if verified_candidates:
                                st.success("Identiteten har oberoende stöd. Exact Comp Hunter är upplåst för denna kandidat.")
                                exact_hunt = hunt_exact_comps(verified_candidates[0], get_sold_comp_data())
                                st.markdown(f"**🎯 Exact Comp Hunter:** {exact_hunt.get('status')}")
                                if exact_hunt.get("query"):
                                    st.code(exact_hunt.get("query"), language=None)
                                exact_count = int(exact_hunt.get("exact_sold_count", 0) or 0)
                                near_count = int(exact_hunt.get("near_sold_count", 0) or 0)
                                st.caption(f"Exakta sålda comps i lokal historik: {exact_count} · nära sålda comps: {near_count}")
                                for comp_item in exact_hunt.get("exact", [])[:3]:
                                    price = comp_item.get("price")
                                    price_text = f" · {price} kr" if price not in (None, "") else ""
                                    st.caption(f"✅ Exakt sold comp{price_text} · {comp_item.get('platform', 'historik')}")
                                for comp_item in exact_hunt.get("near", [])[:2]:
                                    st.caption("🟡 Nära comp – håll separat från exakt kort: " + (comp_item.get("title") or comp_item.get("platform") or "historik"))
                                rejected_count = len(exact_hunt.get("rejected", []))
                                if rejected_count:
                                    st.caption(f"⛔ {rejected_count} historiska poster avvisades p.g.a. identitetskonflikt.")

                                comp_verdict = build_comp_verdict(exact_hunt)
                                verdict_score = int(comp_verdict.get("score", 0) or 0)
                                st.markdown(
                                    f"**🧾 Comp Verdict: {comp_verdict.get('verdict')}** · "
                                    f"{verdict_score}/100 ({comp_verdict.get('level', 'låg')})"
                                )
                                if comp_verdict.get("price_median") is not None:
                                    st.caption(
                                        f"Exakta avslut: {comp_verdict.get('price_low'):.0f}–"
                                        f"{comp_verdict.get('price_high'):.0f} kr · median "
                                        f"{comp_verdict.get('price_median'):.0f} kr"
                                    )
                                dynamic_bid = build_dynamic_max_bid(
                                    base_max_total=candidate.get("max_total_price"),
                                    shipping=candidate.get("max_price_shipping_assumption") or candidate.get("frakt") or 29,
                                    comp_verdict=comp_verdict,
                                )
                                if dynamic_bid.get("available"):
                                    st.success(
                                        f"🎯 Dynamic Max Bid: {dynamic_bid.get('max_item_price', 0):.0f} kr + "
                                        f"{(candidate.get('max_price_shipping_assumption') or candidate.get('frakt') or 29):.0f} kr frakt "
                                        f"(max {dynamic_bid.get('max_total_price', 0):.0f} kr totalt)"
                                    )
                                    base_max = dynamic_bid.get("base_max_total_price")
                                    if base_max is not None and dynamic_bid.get("max_total_price") < base_max:
                                        st.caption(
                                            f"Comp-stödet sänker det ordinarie FlipFynd-taket från {base_max:.0f} till "
                                            f"{dynamic_bid.get('max_total_price', 0):.0f} kr. Det kan aldrig höja budtaket."
                                        )
                                    else:
                                        st.caption("Exact-comp-stödet bekräftar det befintliga konservativa budtaket; det höjs aldrig av Dynamic Max Bid.")
                                elif comp_verdict.get("supports_safe_max_bid"):
                                    st.info("Comp-underlaget är stabilt, men inget befintligt FlipFynd-budtak finns att säkerhetsjustera.")
                                elif exact_count:
                                    st.warning("Comp-underlaget är för svagt eller spretigt för att utfärda Dynamic Max Bid.")
                                with st.expander("Varför denna comp-dom?", expanded=False):
                                    for reason in comp_verdict.get("reasons", [])[:6]:
                                        st.caption("• " + reason)
                                    if dynamic_bid.get("available"):
                                        st.markdown("**Dynamic Max Bid**")
                                        for reason in dynamic_bid.get("reasons", [])[:6]:
                                            st.caption("• " + reason)
                                        st.caption(dynamic_bid.get("note", ""))
                                    st.caption(comp_verdict.get("note", ""))

                                for target in exact_hunt.get("search_targets", []):
                                    st.markdown(f"[{target.get('platform')}: sök exakt kort]({target.get('url')})")
                                    st.caption(target.get("note", ""))
                                st.caption("Exact Comp Hunter organiserar bevis och sökningar. Resultaten måste fortfarande verifieras innan de får påverka värderingen.")
                            else:
                                st.caption("🔒 Exact Comp Hunter låses tills kortidentiteten har tillräckligt oberoende stöd.")
                            st.caption("Bildresultatet och kortkandidaterna är hypoteser och används inte automatiskt i värdering, vinst, Fyndpoäng eller maxbud.")
            st.caption(
                "Bildprioriteten påverkar inte värdering, vinst, ROI eller maxbud. Den avgör bara vilka annonser som bör granskas visuellt först."
            )

    edge_candidates = [
        x for x in filtered
        if x.get("is_market_edge_candidate") and x.get("deal_score", 0) >= 40
    ]
    edge_candidates.sort(
        key=lambda x: (x.get("market_edge_score", 0), x.get("deal_score", 0)), reverse=True
    )
    if edge_candidates:
        with st.expander(f"⚡ Edge Engine ({len(edge_candidates)})", expanded=False):
            st.caption(
                "Här visas annonser där FlipFynd ser en möjlig marknadsfördel – t.ex. svag sökbarhet, "
                "generiska säljarannonser eller mer kortinformation än rubriken avslöjar. Edge skapar aldrig ett marknadsvärde."
            )
            for candidate in edge_candidates[:8]:
                st.write(
                    f"**{candidate.get('titel', 'Okänd annons')}** · "
                    f"Edge {candidate.get('market_edge_score', 0)}/100 · "
                    f"Fyndpoäng {candidate.get('deal_score', 0)}/100"
                )
                if candidate.get("market_edge_reasons"):
                    st.caption(" • ".join(candidate.get("market_edge_reasons")[:3]))
                if candidate.get("lank"):
                    st.markdown(f"[Öppna på Tradera]({candidate.get('lank')})")

    hidden_candidates = [
        x for x in filtered
        if x.get("is_hidden_find_candidate") and x.get("deal_score", 0) >= 45
    ]
    hidden_candidates.sort(key=lambda x: (x.get("hidden_find_score", 0), x.get("deal_score", 0)), reverse=True)
    if hidden_candidates:
        with st.expander(f"🕵️ Dolda fynd ({len(hidden_candidates)})", expanded=False):
            st.caption("Annonser som kan vara svårare för andra köpare att hitta. Märkningen höjer inte marknadsvärdet eller maxbudet.")
            for candidate in hidden_candidates[:8]:
                st.write(
                    f"**{candidate.get('titel', 'Okänd annons')}** · "
                    f"Dold-signal {candidate.get('hidden_find_score', 0)}/100 · "
                    f"Fyndpoäng {candidate.get('deal_score', 0)}/100"
                )
                if candidate.get("hidden_find_reasons"):
                    st.caption(" • ".join(candidate.get("hidden_find_reasons")[:3]))
                if candidate.get("lank"):
                    st.markdown(f"[Öppna på Tradera]({candidate.get('lank')})")

    rookie_hunter_candidates = [
        x for x in filtered
        if x.get("mispriced_rookie_candidate")
    ]
    rookie_hunter_candidates.sort(
        key=lambda x: (x.get("mispriced_rookie_price_gap_supported", False), x.get("mispriced_rookie_score", 0), x.get("deal_score", 0)),
        reverse=True,
    )
    if rookie_hunter_candidates:
        with st.expander(f"🎯 Mispriced Rookie Hunter ({len(rookie_hunter_candidates)})", expanded=False):
            st.caption(
                "Letar efter rookies som verkar underbeskrivna eller missklassificerade. "
                "Det är inte automatiskt ett fynd; prisgap visas bara när befintlig värdering stöds av sold comps."
            )
            for candidate in rookie_hunter_candidates[:8]:
                gap = " · ✅ comp-stött prisgap" if candidate.get("mispriced_rookie_price_gap_supported") else ""
                st.write(
                    f"**{candidate.get('titel', 'Okänd annons')}** · "
                    f"Rookie-edge {int(candidate.get('mispriced_rookie_score', 0) or 0)}/100{gap}"
                )
                if candidate.get("mispriced_rookie_label"):
                    st.caption(candidate.get("mispriced_rookie_label"))
                if candidate.get("mispriced_rookie_reasons"):
                    st.caption(" • ".join(candidate.get("mispriced_rookie_reasons")[:3]))
                if candidate.get("lank"):
                    st.markdown(f"[Öppna på Tradera]({candidate.get('lank')})")

    misclassified_candidates = [
        x for x in filtered
        if x.get("misclassified_card_candidate")
    ]
    misclassified_candidates.sort(
        key=lambda x: (x.get("misclassified_card_price_gap_supported", False), x.get("misclassified_card_score", 0), x.get("deal_score", 0)),
        reverse=True,
    )
    if misclassified_candidates:
        with st.expander(f"🔎 Misclassified Card Hunter ({len(misclassified_candidates)})", expanded=False):
            st.caption(
                "Letar efter underbeskrivna paralleller, autos, patchar, SSP/case hits, lågnumrerade kort och 1/1. "
                "Discovery-signalen höjer inte värde eller maxbud."
            )
            for candidate in misclassified_candidates[:8]:
                gap = " · ✅ comp-stött prisgap" if candidate.get("misclassified_card_price_gap_supported") else ""
                st.write(
                    f"**{candidate.get('titel', 'Okänd annons')}** · "
                    f"Missklassificerings-edge {int(candidate.get('misclassified_card_score', 0) or 0)}/100{gap}"
                )
                if candidate.get("misclassified_card_label"):
                    st.caption(candidate.get("misclassified_card_label"))
                if candidate.get("misclassified_card_target_tags"):
                    st.caption("Korttyp: " + ", ".join(candidate.get("misclassified_card_target_tags")[:4]))
                if candidate.get("misclassified_card_reasons"):
                    st.caption(" • ".join(candidate.get("misclassified_card_reasons")[:3]))
                if candidate.get("lank"):
                    st.markdown(f"[Öppna på Tradera]({candidate.get('lank')})")

    if len(visible) >= 2:
        first, second = visible[0], visible[1]
        with st.expander("Varför ligger #1 före #2?", expanded=False):
            first_name = first.get("titel", "#1")
            second_name = second.get("titel", "#2")
            st.write(f"**#1:** {first_name}")
            st.write(f"**#2:** {second_name}")
            for explanation in explain_rank_advantage(first, second):
                st.write(f"• {explanation}")
            st.caption(
                "Jämförelsen förklarar den aktuella FlipFynd-rankningen – den är inte ett löfte om framtida försäljningspris."
            )

    for index, item in enumerate(visible, start=1):
        raw_decision = item.get("beslut", "SKIP")
        if raw_decision == "KÖP (starkt fynd)":
            decision_label = "🟢 STARKT FYND"
            decision_help = "Analysen bedömer både vinstpotential och säljsannolikhet som starka."
        elif raw_decision == "KÖP":
            decision_label = "🟢 KÖP"
            decision_help = "Kortet passerar FlipFynds köpgränser för vinst och säljsannolikhet."
        elif raw_decision == "KANSKE":
            decision_label = "🟡 BEVAKA"
            decision_help = "Potential finns, men marginal eller säljsannolikhet är inte tillräckligt stark för ett tydligt köp."
        else:
            decision_label = "🔴 HOPPA ÖVER"
            decision_help = "Risk, låg efterfrågan eller för liten marginal gör kortet svagt för vidareförsäljning."

        total_cost = item.get("total_cost", 0) or 0
        analysis_total_cost = item.get("analysis_total_cost", total_cost) or total_cost
        sale_type = item.get("sale_type", "Okänd") or "Okänd"
        auction_buffer = item.get("auction_buffer", 0) or 0
        expected = item.get("expected_resale", 0) or 0
        floor = item.get("floor_resale", 0) or 0
        best_case = item.get("best_case_resale", 0) or 0
        net_profit = item.get("net_profit_estimate", 0) or 0
        sale_probability = item.get("sale_probability", 0) or 0

        with st.container(border=True):
            decision_class = "buy" if raw_decision.startswith("KÖP") else ("watch" if raw_decision == "KANSKE" else "skip")
            decision_text = "STARKT FYND" if raw_decision == "KÖP (starkt fynd)" else ("KÖP" if raw_decision == "KÖP" else ("BEVAKA" if raw_decision == "KANSKE" else "HOPPA ÖVER"))
            score_value = float(item.get("deal_score", 0) or 0)
            quick_price_label = "AKTUELLT" if sale_type == "Auktion" else "KÖP FÖR"
            quick_resale = f"{floor:.0f}–{expected:.0f} kr" if floor and expected and floor != expected else f"{expected:.0f} kr"
            result_html = f"""<div class="ff-result-head">
                    <div class="ff-result-topline">
                      <span class="ff-rank-chip">RANK #{index:02d}</span>
                      <span class="ff-decision-chip {decision_class}">{decision_text}</span>
                      <span class="ff-score-chip">FYND {score_value:.0f}/100</span>
                    </div>
                    <div class="ff-result-title">{item.get('titel', '')}</div>
                    <div class="ff-result-sub">{decision_help}</div>
                    <div class="ff-quick-grid">
                      <div class="ff-quick-cell"><div class="ff-quick-label">{quick_price_label}</div><div class="ff-quick-value">{total_cost:.0f} kr</div></div>
                      <div class="ff-quick-cell"><div class="ff-quick-label">REALISTISKT VÄRDE</div><div class="ff-quick-value">{quick_resale}</div></div>
                      <div class="ff-quick-cell"><div class="ff-quick-label">MÖJLIG NETTOVINST</div><div class="ff-quick-value">{net_profit:.0f} kr</div></div>
                      <div class="ff-quick-cell"><div class="ff-quick-label">SÄLJCHANS</div><div class="ff-quick-value">{sale_probability:.0f}%</div></div>
                    </div>
                    <div class="ff-retro-rule"></div>
                  </div>"""
            st.markdown(result_html, unsafe_allow_html=True)

            if item.get("visual_image_urls"):
                img_cols = st.columns(min(3, len(item.get("visual_image_urls")[:3])))
                for img_col, img_url in zip(img_cols, item.get("visual_image_urls")[:3]):
                    with img_col:
                        st.image(img_url, use_container_width=True)
            if item.get("visual_verification_required"):
                st.info(
                    f"👁️ {item.get('visual_edge_label', 'Bildkontroll')} · "
                    f"{float(item.get('visual_edge_score', 0)):.0f}/100 — "
                    + " • ".join(item.get("visual_edge_reasons", [])[:2])
                )
                st.caption("Visual Edge är en granskningssignal. Bildinnehållet är ännu inte automatiskt verifierat av modellen.")

            m1, m2 = st.columns(2)
            with m1:
                if sale_type == "Auktion":
                    st.metric("Aktuellt pris inkl. frakt", f"{total_cost:.0f} kr")
                    st.caption(
                        f"Fyndkalkylen räknar på {analysis_total_cost:.0f} kr"
                        + (f" inklusive {auction_buffer:.0f} kr auktionsbuffert." if auction_buffer else ".")
                    )
                else:
                    st.metric("Köp för inkl. frakt", f"{total_cost:.0f} kr")
            with m2:
                st.metric("Möjlig nettovinst", f"{net_profit:.0f} kr")

            max_total_price = item.get("max_total_price")
            max_item_price = item.get("max_item_price")
            max_shipping = item.get("max_price_shipping_assumption")
            if max_total_price is not None and max_item_price is not None:
                if sale_type == "Auktion":
                    st.success(
                        f"🎯 Max bud: {max_item_price:.0f} kr"
                        f" + {max_shipping:.0f} kr frakt"
                        f" (max {max_total_price:.0f} kr totalt)"
                    )
                    st.caption(
                        "Över den nivån når kortet inte längre FlipFynds KÖP-gräns "
                        "med dagens värdering och riskantaganden."
                    )
                    bid_strategy = item.get("auction_bid_strategy") or {}
                    if bid_strategy:
                        status = bid_strategy.get("status", "BEVAKA")
                        margin = bid_strategy.get("remaining_bid_margin", 0) or 0
                        if status == "STOPP":
                            st.error(f"🛑 {status} · budtaket är nått")
                        elif status == "NÄRA BUDTAK":
                            st.warning(f"⚠️ {status} · bara {margin:.0f} kr marginal kvar")
                        elif status == "BEVAKA":
                            st.info(f"👀 {status} · {margin:.0f} kr marginal till budtaket")
                        else:
                            st.info(f"⏳ {status} · {margin:.0f} kr marginal till budtaket")
                        st.caption(bid_strategy.get("message", ""))
                else:
                    st.success(f"🎯 Max köppris inkl. frakt: {max_total_price:.0f} kr")
                    st.caption(
                        "Högsta beräknade totalkostnad som fortfarande når FlipFynds KÖP-gräns."
                    )

            if item.get("is_market_edge_candidate"):
                st.info(
                    f"⚡ {item.get('market_edge_label', 'Marknadsedge')} · "
                    f"{item.get('market_edge_score', 0)}/100 — "
                    + " • ".join(item.get("market_edge_reasons", [])[:2])
                )

            if item.get("is_hidden_find_candidate"):
                st.info(
                    f"🕵️ {item.get('hidden_find_label', 'Dolt fynd-kandidat')} · "
                    f"synlighetssignal {item.get('hidden_find_score', 0)}/100. "
                    "Detta är en sökbarhetssignal – inte ett värdebevis."
                )

            m3, m4, m5, m6 = st.columns(4)
            with m3:
                st.metric("Fyndpoäng", f"{item.get('deal_score', 0):.0f}/100")
                st.caption(item.get("deal_score_label", "Pass"))
            with m4:
                if floor and expected and floor != expected:
                    resale_text = f"{floor:.0f}–{expected:.0f} kr"
                else:
                    resale_text = f"{expected:.0f} kr"
                st.metric("Realistiskt värde", resale_text)
            with m5:
                st.metric("Säljbarhet", item.get("liquidity_label", "Normalt"))
                st.caption(f"{item.get('liquidity_score', 0):.0f}/100 • säljchans {sale_probability:.0f}%")
            with m6:
                deal_confidence = item.get("deal_confidence_score", 0) or 0
                st.metric("Fyndsäkerhet", f"{deal_confidence:.0f}/100")
                st.caption(f"{item.get('deal_confidence_level', 'låg')} evidens")

            risk_score = item.get("risk_score")
            if risk_score is not None:
                risk_level = item.get("risk_label", item.get("risk_level", "Okänd"))
                st.caption(
                    f"Risk: {risk_level} ({float(risk_score):.0f}/100) • "
                    f"maxbud riskjusterat till {float(item.get('risk_max_bid_factor', 1.0)) * 100:.0f}% av normal kalkyl"
                )

            valuation_confidence_score = item.get("valuation_confidence_score")
            if valuation_confidence_score is not None and item.get("comp_valuation_basis") != "none":
                basis_text = "sålda comps" if item.get("comp_valuation_basis") == "sold" else "aktiva annonser"
                st.caption(
                    f"Värderingssäkerhet: {float(valuation_confidence_score):.0f}/100 "
                    f"({item.get('valuation_confidence_level', 'låg')}) • {basis_text}"
                )

            why_bits = []
            player = item.get("player_name")
            if player:
                why_bits.append(player)
            demand = item.get("demand_tier")
            if demand:
                why_bits.append(f"efterfrågan: {demand}")
            exit_speed = item.get("exit_speed")
            if exit_speed:
                why_bits.append(f"exit: {exit_speed}")

            if why_bits:
                st.caption(" • ".join(why_bits))

            identity_score = item.get("card_identity_confidence_score")
            if identity_score is not None:
                st.caption(f"Kortidentifiering: {float(identity_score):.0f}/100")
            if item.get("identity_conflicts"):
                st.warning("⚠️ Motstridig kortinformation i annonsen. Manuell kontroll rekommenderas.")

            player_match_confidence = item.get("player_match_confidence", "low")
            if player_match_confidence == "medium":
                st.caption("⚠️ Spelarnamnet identifierades med stavningstolerans – kontrollera titeln före köp.")
            elif player_match_confidence == "low":
                st.caption("⚠️ Osäker spelaridentifiering. FlipFynd tillåter inte ett tydligt köpbeslut på den här träffen.")

            decision_diagnostics = item.get("decision_diagnostics") or []
            if decision_diagnostics and raw_decision in {"SKIP", "KANSKE"}:
                with st.expander("Varför når kortet inte KÖP?"):
                    for diagnostic in decision_diagnostics:
                        st.write(f"• {diagnostic}")

            if item.get("kommentar"):
                st.write(item["kommentar"])

            if item.get("lank"):
                st.link_button(
                    "Öppna annons på Tradera ↗",
                    item["lank"],
                    use_container_width=True,
                )

            with st.expander("Visa full analys"):
                d1, d2 = st.columns(2)
                with d1:
                    st.write(f"**Pris:** {item.get('pris', 0)} kr")
                    shipping_raw = item.get("frakt")
                    shipping_text = (
                        f"{shipping_raw} kr"
                        if shipping_raw is not None
                        else f"okänd – {DEFAULT_UNKNOWN_SHIPPING} kr antaget i kalkylen"
                    )
                    st.write(f"**Frakt:** {shipping_text}")
                    st.write(f"**Spelare:** {player or 'Okänd'}")
                    st.write(f"**Spelarscore:** {item.get('player_market_score', 0)}/100")
                    st.write(f"**Spelar-ID:** {item.get('player_match_confidence', 'low')}")
                    st.write(f"**Efterfrågan:** {demand or 'Okänd'}")
                    st.write(f"**Annonsform:** {item.get('sale_type', '')}")
                    st.write(
                        f"**Annonskvalitet:** {item.get('listing_quality_level', 'okänd')} "
                        f"({item.get('listing_quality_score', 0)}/100)"
                    )
                    st.write(
                        f"**Fyndsäkerhet:** {item.get('deal_confidence_level', 'låg')} "
                        f"({item.get('deal_confidence_score', 0)}/100)"
                    )
                    st.write(
                        f"**Fyndpoäng:** {item.get('deal_score', 0)}/100 – "
                        f"{item.get('deal_score_label', 'Pass')}"
                    )
                    st.write(
                        f"**Säljbarhet:** {item.get('liquidity_label', 'Okänd')} "
                        f"({item.get('liquidity_score', 0)}/100; {item.get('liquidity_evidence', 'heuristic')})"
                    )
                    st.write(
                        f"**Värderingssäkerhet:** {item.get('valuation_confidence_level', 'mycket låg')} "
                        f"({item.get('valuation_confidence_score', 10)}/100)"
                    )
                    st.write(
                        f"**Risk:** {item.get('risk_label', 'Okänd')} "
                        f"({item.get('risk_score', 0)}/100)"
                    )
                    if item.get("card_identity"):
                        st.write(f"**Kortidentitet:** {item.get('card_identity')}")

                with d2:
                    st.write(f"**Försiktigt värde:** {floor:.0f} kr")
                    st.write(f"**Förväntat värde:** {expected:.0f} kr")
                    st.write(f"**Best case:** {best_case:.0f} kr")
                    st.write(f"**Riskjusterad vinst:** {item.get('risk_adjusted_profit', 0)} kr")
                    st.write(f"**ROI:** {item.get('roi_estimate', 0)}")
                    st.write(f"**Rank:** {item.get('rank_score', 0)}")
                    st.caption(
                        f"Ranken vägs med fyndsäkerhet: {item.get('ranking_confidence_score', item.get('deal_confidence_score', 0))}/100"
                    )

                valuation_reasons = item.get("valuation_confidence_reasons") or []
                if valuation_reasons and item.get("comp_valuation_basis") != "none":
                    with st.expander("Varför denna värderingssäkerhet?"):
                        for reason in valuation_reasons:
                            st.write(f"• {reason}")

                knowledge_signals = item.get("market_knowledge_signals") or []
                if knowledge_signals:
                    labels = ", ".join(str(sig.get("label")) for sig in knowledge_signals if sig.get("label"))
                    if labels:
                        top_priority = max((int(sig.get("attention_priority", 0) or 0) for sig in knowledge_signals), default=0)
                        priority_text = "mycket hög" if top_priority >= 5 else "hög" if top_priority >= 4 else "förhöjd" if top_priority >= 3 else "normal"
                        st.info(
                            f"Känd samlarsignal: {labels}. Granskningsprioritet: {priority_text}. "
                            "Detta hjälper FlipFynd att inte missa viktiga varianter, men skapar aldrig ett marknadsvärde utan comps."
                        )

                    intelligence_summary = item.get("card_intelligence_summary")
                    intelligence_reasons = item.get("card_intelligence_reasons") or []
                    intelligence_paths = item.get("card_intelligence_paths") or []
                    intelligence_checks = item.get("card_intelligence_verification_steps") or []
                    if intelligence_summary:
                        with st.expander("🧠 Varför är denna korttyp viktig?"):
                            st.write(intelligence_summary)
                            if intelligence_paths:
                                st.write("**Kortets struktur i kunskapsbanken**")
                                for path in intelligence_paths[:4]:
                                    st.write(f"• {path}")
                            if intelligence_reasons:
                                st.write("**Varför FlipFynd reagerar**")
                                for reason in intelligence_reasons[:4]:
                                    st.write(f"• {reason}")
                            if intelligence_checks:
                                st.write("**Kontroll före värdering**")
                                for check in intelligence_checks[:4]:
                                    st.write(f"• {check}")
                            st.caption(
                                "Kunskapsbanken beskriver kortstruktur och samlarrelevans. "
                                "Den får inte skapa pris, vinst eller maxbud utan marknadsdata."
                            )

                library_families = item.get("card_knowledge_library_families") or []
                if library_families:
                    with st.expander("📚 Card Knowledge Library"):
                        if item.get("card_knowledge_library_summary"):
                            st.write(item.get("card_knowledge_library_summary"))
                        for family in library_families[:4]:
                            product = family.get("product_family", "Okänd produkt")
                            program = family.get("program_family", "Okänt program")
                            matched = family.get("matched_variant", "Okänd variant")
                            st.write(f"**{product} → {program} → {matched}**")
                            siblings = family.get("sibling_variants") or []
                            if siblings:
                                labels = []
                                for sibling in siblings[:6]:
                                    label = str(sibling.get("label") or "")
                                    if sibling.get("print_run"):
                                        label += f" /{sibling.get('print_run')}"
                                    if label:
                                        labels.append(label)
                                if labels:
                                    st.caption("Relaterade varianter i samma familj: " + " • ".join(labels))
                        boundaries = item.get("card_knowledge_library_comp_boundaries") or []
                        if boundaries:
                            st.write("**Comp-gränser**")
                            for boundary in boundaries[:6]:
                                st.write(f"• {boundary}")
                        st.caption(
                            item.get("card_knowledge_library_note")
                            or "Biblioteket beskriver kortfamiljer och får inte skapa pris eller maxbud utan marknadsdata."
                        )

                variant_rung = int(item.get("variant_hierarchy_variant_rung") or 0)
                rookie_rung = int(item.get("variant_hierarchy_rookie_rung") or 0)
                if variant_rung or rookie_rung:
                    with st.expander("🪜 Variant Ladder & Rookie Hierarchy"):
                        if item.get("variant_hierarchy_summary"):
                            st.write(item.get("variant_hierarchy_summary"))
                        c1, c2 = st.columns(2)
                        c1.metric(
                            "Variantnivå",
                            f"{variant_rung}/6",
                            item.get("variant_hierarchy_variant_label") or "Okänd",
                        )
                        c2.metric(
                            "Rookienivå",
                            f"{rookie_rung}/5",
                            item.get("variant_hierarchy_rookie_label") or "Ej rookie",
                        )
                        paths = item.get("variant_hierarchy_paths") or []
                        if paths:
                            st.write("**Placering i kortfamiljen**")
                            for path in paths[:5]:
                                st.write(f"• {path}")
                        reasons = item.get("variant_hierarchy_reasons") or []
                        if reasons:
                            st.write("**Strukturell betydelse**")
                            for reason in reasons[:5]:
                                st.write(f"• {reason}")
                        checks = item.get("variant_hierarchy_verification_steps") or []
                        if checks:
                            st.write("**Verifiera före comp**")
                            for check in checks[:5]:
                                st.write(f"• {check}")
                        st.caption(
                            item.get("variant_hierarchy_note")
                            or "Hierarkin beskriver kortstruktur, inte marknadsvärde."
                        )

                matrix_score = item.get("collector_intelligence_score")
                if matrix_score is not None:
                    with st.expander("🧬 Collector Intelligence Matrix"):
                        st.write(
                            f"**{item.get('collector_intelligence_label', 'Samlarrelevans')} – "
                            f"{matrix_score}/100 ({item.get('collector_intelligence_level', '')})**"
                        )
                        if item.get("collector_intelligence_archetype"):
                            st.write(f"**Typ:** {item.get('collector_intelligence_archetype')}")
                        for reason in (item.get("collector_intelligence_reasons") or [])[:6]:
                            st.write(f"• {reason}")
                        if item.get("collector_intelligence_next_action"):
                            st.info(item.get("collector_intelligence_next_action"))
                        st.caption(
                            item.get("collector_intelligence_note")
                            or "Matrisen är kunskapsstöd, inte en prisguide."
                        )

                if item.get("detail_enrichment_status") == "ok":
                    with st.expander("🔍 Smart Listing Detail Enrichment"):
                        e1, e2 = st.columns(2)
                        e1.metric("Detaljprioritet", f"{int(item.get('detail_priority_score') or 0)}/100")
                        e2.metric("Bud", item.get("bid_count") if item.get("bid_count") is not None else "–")
                        if item.get("exact_end_text"):
                            st.write(f"**Sluttid enligt annonsen:** {item.get('exact_end_text')}")
                        if item.get("seller_detail"):
                            st.write(f"**Säljare enligt detaljsidan:** {item.get('seller_detail')}")
                        description = item.get("full_description")
                        if description:
                            st.write("**Beskrivning från annonsen**")
                            st.write(description[:1800])
                        detail_images = item.get("detail_image_urls") or []
                        if detail_images:
                            st.caption(f"{len(detail_images)} bildreferenser hittades på detaljsidan.")
                        reasons = item.get("detail_priority_reasons") or []
                        if reasons:
                            st.caption("Öppnades för detaljkontroll eftersom: " + ", ".join(reasons[:5]))
                        st.caption(
                            "Detaljberikningen samlar synlig metadata. Den skapar inte i sig värde, ROI eller maxbud."
                        )

                fusion_score = item.get("detail_evidence_fusion_score")
                if fusion_score is not None:
                    with st.expander("🧩 Detail Evidence Fusion"):
                        f1, f2, f3 = st.columns(3)
                        f1.metric("Evidensstyrka", f"{int(fusion_score or 0)}/100")
                        f2.metric("Källor", int(item.get("detail_evidence_fusion_source_count") or 0))
                        f3.metric("Status", item.get("detail_evidence_fusion_status") or "–")
                        corroborated = item.get("detail_evidence_fusion_corroborated_fields") or []
                        if corroborated:
                            st.success("Samma identitet stöds av flera källor för: " + ", ".join(corroborated[:6]))
                        discoveries = item.get("detail_evidence_fusion_discoveries") or []
                        if discoveries:
                            st.write("**Nya identitetsdetaljer utanför titeln**")
                            for discovery in discoveries[:6]:
                                st.write(f"• {discovery}")
                        conflicts = item.get("detail_evidence_fusion_conflicts") or []
                        if conflicts:
                            st.error("Konflikt mellan evidenskällor – hunter-signaler spärras tills detta verifierats.")
                            for conflict in conflicts[:6]:
                                st.write(f"• {conflict}")
                        st.caption(
                            item.get("detail_evidence_fusion_note")
                            or "Evidence Fusion används för identitetskontroll och skapar inte värde eller köpbeslut."
                        )

                demand_score = item.get("player_card_demand_score")
                if demand_score is not None:
                    with st.expander("🎯 Player × Card Demand Engine"):
                        d1, d2, d3 = st.columns(3)
                        d1.metric("Efterfrågan", f"{int(demand_score or 0)}/100")
                        d2.metric("Evidenssäkerhet", f"{int(item.get('player_card_demand_confidence_score') or 0)}/100")
                        d3.metric("Analysprioritet", f"{int(item.get('player_card_demand_review_priority_score') or 0)}/100")
                        if item.get("player_card_demand_profile"):
                            st.write(f"**Profil:** {item.get('player_card_demand_profile')}")
                        comp_cols = st.columns(3)
                        comp_cols[0].caption(f"Spelare: {int(item.get('player_card_demand_player_component') or 0)}/100")
                        comp_cols[1].caption(f"Kortstruktur: {int(item.get('player_card_demand_structure_component') or 0)}/100")
                        comp_cols[2].caption(f"Marknad: {int(item.get('player_card_demand_market_component') or 0)}/100")
                        if item.get("player_card_demand_market_evidence"):
                            st.write(f"**Marknadsevidens:** {item.get('player_card_demand_market_evidence')}")
                        for reason in (item.get("player_card_demand_reasons") or [])[:5]:
                            st.write(f"• {reason}")
                        cautions = item.get("player_card_demand_cautions") or []
                        if cautions:
                            st.write("**Osäkerheter**")
                            for caution in cautions[:4]:
                                st.write(f"• {caution}")
                        if item.get("player_card_demand_next_action"):
                            st.info(item.get("player_card_demand_next_action"))
                        st.caption(
                            item.get("player_card_demand_note")
                            or "Efterfrågemotorn prioriterar analys och är inte en prisguide."
                        )

                valuable_priority = item.get("valuable_card_priority_score")
                if valuable_priority is not None and int(valuable_priority or 0) > 0:
                    with st.expander("💰 Valuable Card Knowledge Engine"):
                        v1, v2, v3 = st.columns(3)
                        v1.metric("Granskningsprioritet", f"{int(valuable_priority or 0)}/100")
                        v2.metric("Kortstruktur", f"{int(item.get('valuable_card_structure_score') or 0)}/100")
                        v3.metric("Marknadsevidens", f"{int(item.get('valuable_card_market_evidence_score') or 0)}/100")
                        if item.get("valuable_card_archetype"):
                            st.write(f"**Korttyp:** {item.get('valuable_card_archetype')}")
                        tags = item.get("valuable_card_tags") or []
                        if tags:
                            st.write("**Värdekortssignaler:** " + " · ".join(tags[:6]))
                        if item.get("valuable_card_market_evidence"):
                            st.write(f"**Evidens:** {item.get('valuable_card_market_evidence')}")
                        for reason in (item.get("valuable_card_reasons") or [])[:5]:
                            st.write(f"• {reason}")
                        cautions = item.get("valuable_card_cautions") or []
                        if cautions:
                            st.write("**Viktiga spärrar**")
                            for caution in cautions[:5]:
                                st.write(f"• {caution}")
                        st.caption(
                            item.get("valuable_card_note")
                            or "Korttypen styr granskningsprioritet, inte marknadsvärde."
                        )

                rookie_importance_score = item.get("rookie_importance_score")
                if item.get("rookie_importance_matched") and int(rookie_importance_score or 0) > 0:
                    with st.expander("🌱 Player Rookie Importance Engine"):
                        r1, r2 = st.columns(2)
                        r1.metric("Rookie-vikt", f"{int(rookie_importance_score or 0)}/100")
                        r2.metric("Spelare", f"{int(item.get('valuable_card_player_score') or 0)}/100")
                        if item.get("rookie_importance_tier"):
                            st.write(f"**Programnivå:** {item.get('rookie_importance_tier')}")
                        if item.get("rookie_importance_status"):
                            st.write(f"**Status:** {item.get('rookie_importance_status')}")
                        if item.get("rookie_importance_key_status"):
                            if item.get("rookie_importance_safe_key"):
                                st.success(item.get("rookie_importance_key_status"))
                            else:
                                st.warning(item.get("rookie_importance_key_status"))
                        for reason in (item.get("rookie_importance_reasons") or [])[:5]:
                            st.write(f"• {reason}")
                        cautions = item.get("rookie_importance_cautions") or []
                        if cautions:
                            st.write("**Verifiera innan du kallar det nyckelrookie**")
                            for caution in cautions[:5]:
                                st.write(f"• {caution}")
                        if item.get("rookie_importance_next_action"):
                            st.info(item.get("rookie_importance_next_action"))
                        st.caption(item.get("rookie_importance_note") or "Rookie-vikt styr verifieringsprioritet, inte pris.")

                mispriced_rookie_score = item.get("mispriced_rookie_score")
                if item.get("mispriced_rookie_candidate") and int(mispriced_rookie_score or 0) > 0:
                    with st.expander("🎯 Mispriced Rookie Hunter"):
                        m1, m2 = st.columns(2)
                        m1.metric("Rookie-edge", f"{int(mispriced_rookie_score or 0)}/100")
                        m2.metric(
                            "Prisgap",
                            "Comp-stött" if item.get("mispriced_rookie_price_gap_supported") else "Ej verifierat",
                        )
                        if item.get("mispriced_rookie_label"):
                            st.write(f"**Signal:** {item.get('mispriced_rookie_label')}")
                        for reason in (item.get("mispriced_rookie_reasons") or [])[:6]:
                            st.write(f"• {reason}")
                        cautions = item.get("mispriced_rookie_cautions") or []
                        if cautions:
                            st.write("**Verifiera först**")
                            for caution in cautions[:5]:
                                st.write(f"• {caution}")
                        if item.get("mispriced_rookie_next_action"):
                            st.info(item.get("mispriced_rookie_next_action"))
                        st.caption(
                            item.get("mispriced_rookie_note")
                            or "Rookie Hunter är en discovery-signal och får inte skapa värde eller maxbud."
                        )

                misclassified_score = item.get("misclassified_card_score")
                if item.get("misclassified_card_candidate") and int(misclassified_score or 0) > 0:
                    with st.expander("🔎 Misclassified Card Hunter"):
                        c1, c2 = st.columns(2)
                        c1.metric("Missklassificerings-edge", f"{int(misclassified_score or 0)}/100")
                        c2.metric("Prisgap", "Comp-stött" if item.get("misclassified_card_price_gap_supported") else "Ej verifierat")
                        if item.get("misclassified_card_label"):
                            st.write(f"**Signal:** {item.get('misclassified_card_label')}")
                        if item.get("misclassified_card_target_tags"):
                            st.write("**Identifierad struktur:** " + ", ".join(item.get("misclassified_card_target_tags")[:6]))
                        for reason in (item.get("misclassified_card_reasons") or [])[:6]:
                            st.write(f"• {reason}")
                        cautions = item.get("misclassified_card_cautions") or []
                        if cautions:
                            st.write("**Verifiera först**")
                            for caution in cautions[:5]:
                                st.write(f"• {caution}")
                        if item.get("misclassified_card_next_action"):
                            st.info(item.get("misclassified_card_next_action"))
                        st.caption(item.get("misclassified_card_note") or "Discovery-signal – inte värderingsunderlag.")

                chase_priority = item.get("chase_knowledge_priority_score")
                if chase_priority is not None and int(chase_priority or 0) > 0:
                    with st.expander("💎 Grail & Chase Knowledge Graph"):
                        st.write(
                            f"**{item.get('chase_knowledge_level', 'Chase-prioritet')} – "
                            f"{int(chase_priority)}/100**"
                        )
                        if item.get("chase_knowledge_profile"):
                            st.write(f"**Profil:** {item.get('chase_knowledge_profile')}")
                        for reason in (item.get("chase_knowledge_reasons") or [])[:6]:
                            st.write(f"• {reason}")
                        checks = item.get("chase_knowledge_verification_steps") or []
                        if checks:
                            st.write("**Verifiera innan värdering**")
                            for check in checks[:5]:
                                st.write(f"• {check}")
                        nodes = item.get("chase_knowledge_nodes") or []
                        if nodes:
                            path_labels = [n.get("label") for n in nodes if n.get("type") in {"product", "program", "variant"} and n.get("label")]
                            if path_labels:
                                st.caption("Kunskapsgraf: " + " → ".join(dict.fromkeys(path_labels[:5])))
                        st.caption(
                            item.get("chase_knowledge_note")
                            or "Chase-kunskap är inte en prisguide och får inte skapa maxbud utan comps."
                        )

                flip_scenarios = item.get("flip_scenarios") or []
                if flip_scenarios:
                    st.write("**🎬 Flip Scenario Engine**")
                    st.caption(item.get("flip_scenario_summary") or "Tre scenarier baserade på befintlig värdering.")
                    cols = st.columns(3)
                    for scenario, col in zip(flip_scenarios[:3], cols):
                        with col:
                            st.markdown(f"**{scenario.get('label', 'Scenario')}**")
                            st.metric("Säljpris", f"{scenario.get('resale_price', 0):.0f} kr")
                            st.metric("Nettovinst", f"{scenario.get('net_profit', 0):.0f} kr")
                            st.caption(
                                f"ROI {scenario.get('roi', 0) * 100:.0f}% • "
                                f"{scenario.get('sellability_label', 'Okänd säljbarhet')}"
                            )
                    if item.get("flip_scenario_resilient"):
                        st.success("Robust flip: kalkylen är fortfarande attraktiv i scenariot Snabb försäljning.")
                    else:
                        st.info("Kontrollera särskilt scenariot Snabb försäljning – där syns affärens nedsida tydligast.")
                    st.caption(item.get("flip_scenario_note") or "")

                comp_range = item.get("comp_valuation_range") or {}
                if comp_range and comp_range.get("basis") == "sold":
                    st.write("**Observerat försäljningsintervall**")
                    st.write(
                        f"Låg {comp_range.get('low', 0):.0f} kr • "
                        f"Trolig {comp_range.get('base', 0):.0f} kr • "
                        f"Hög {comp_range.get('high', 0):.0f} kr"
                    )
                    st.caption(
                        f"Bygger på realiserade försäljningar • comp-confidence: {comp_range.get('confidence', 'låg')}"
                    )

                sold_comp_count = int(item.get("sold_comparable_count", 0) or 0)
                asking_comp_count = int(item.get("asking_comparable_count", 0) or 0)
                comp_basis = item.get("comp_valuation_basis", "none")
                if sold_comp_count or asking_comp_count:
                    st.write("**Comparable sales / marknadsstöd**")
                    if comp_basis == "sold":
                        st.success(
                            f"Värderingen stöds primärt av {sold_comp_count} verifierade sålda comps. "
                            f"{asking_comp_count} aktiva annonser används endast som sekundärt stöd."
                        )
                    else:
                        st.warning(
                            f"Verifierade sålda comps saknas eller är för få. "
                            f"{asking_comp_count} aktiva annonser används konservativt som stöd – de är inte försäljningspriser."
                        )

                    comp_details = item.get("comparable_details") or []
                    if comp_details:
                        with st.expander("Visa jämförelseobjekt"):
                            for comp in comp_details[:8]:
                                state = comp.get("market_state")
                                state_text = "SÅLT" if state == "sold" else "AKTIV ANNONS"
                                price = comp.get("price")
                                price_text = f"{price:.0f} kr" if isinstance(price, (int, float)) else "pris saknas"
                                age = comp.get("age_days")
                                age_text = f" • {age} dagar sedan" if isinstance(age, int) else ""
                                platform = comp.get("platform") or "Okänd plattform"
                                match_quality = comp.get("match_quality") or "okänd"
                                st.write(
                                    f"**{state_text}** • {price_text}{age_text} • {platform} • match: {match_quality}"
                                )
                                if comp.get("title"):
                                    st.caption(comp.get("title"))

                rejected_comp_count = int(item.get("rejected_comparable_count", 0) or 0)
                rejected_comps = item.get("rejected_comparables") or []
                if rejected_comp_count:
                    st.caption(
                        f"{rejected_comp_count} jämförelseobjekt har uteslutits eftersom en identifierad "
                        "variantdetalj inte matchar kortet."
                    )
                    with st.expander("Visa uteslutna comps"):
                        for rejected in rejected_comps[:8]:
                            reasons = "; ".join(rejected.get("reasons") or [])
                            title = rejected.get("title") or "Jämförelseobjekt"
                            st.write(f"**{title}**")
                            if reasons:
                                st.caption(reasons)

                strengths = item.get("deal_confidence_strengths") or []
                weaknesses = item.get("deal_confidence_weaknesses") or []
                if strengths or weaknesses:
                    st.write("**Vad bygger fyndsäkerheten på?**")
                    for strength in strengths:
                        st.write(f"✓ {strength}")
                    for weakness in weaknesses:
                        st.write(f"⚠️ {weakness}")

                reasons = item.get("reasons", [])
                if reasons:
                    st.write("**Varför rankas kortet så här?**")
                    for reason in reasons:
                        st.write(f"- {reason}")

                risk_reasons = item.get("risk_reasons") or []
                if risk_reasons:
                    with st.expander("Varför denna risknivå?"):
                        for reason in risk_reasons:
                            st.write(f"• {reason}")

                risks = item.get("risk_flags", [])
                if risks:
                    st.write("**Risker**")
                    for risk in risks:
                        st.write(f"- {risk}")

                st.caption(f"Säljare: {get_seller(item)}")


fetch_state = load_fetch_state()

st.divider()
with st.expander("⚙️ Administration & data"):
    st.caption(
        "Standardvalet uppdaterar både hockey och fotboll automatiskt. "
        f"Smart uppdatering läser högst {SMART_MAX_PAGES} av de nyaste sidorna per sport och stoppar tidigare "
        "när marknaden redan är känd. Det håller Streamlit-belastningen nere."
    )

    category_infos = fetch_state.get("categories", {})
    summary_cols = st.columns(2)
    for idx, category_name in enumerate(CATEGORY_URLS.keys()):
        info = category_infos.get(category_name, {})
        sport_name = "Hockey" if "Hockey" in category_name else "Fotboll"
        with summary_cols[idx]:
            st.markdown(f"**{sport_name}**")
            st.write(f"Senast uppdaterad: {format_last_fetch_time(info.get('last_fetch_at'))}")
            if info.get("running"):
                current_page = int(info.get("current_page", 0) or 0)
                current_seen = int(info.get("current_items_seen", 0) or 0)
                current_new = int(info.get("current_new_items", 0) or 0)
                st.info(
                    f"Pågår: sida {current_page} • {current_seen} annonser lästa • {current_new} nya"
                )
            elif info.get("last_fetch_at"):
                last_new = int(info.get("last_new_items", 0) or 0)
                last_pages = int(info.get("last_pages_scanned", 0) or 0)
                last_stop = info.get("last_stop_reason", "")
                st.caption(
                    f"{last_pages} sidor • {last_new} nya annonser"
                    + (f" • stopp: {last_stop}" if last_stop else "")
                )

    with st.expander("Avancerade hämtningsinställningar"):
        headless = st.checkbox(
            "Kör browsern i bakgrunden",
            value=True,
            key="admin_headless",
        )
        mode_label = st.radio(
            "Hämtläge",
            ["Smart uppdatering", "Smart refresh – bara gamla sidor", "Läs nästa marknadsomgång", "Full genomsökning"],
            key="admin_mode",
            help=(
                f"Smart uppdatering börjar på sida 1, stoppar efter två hela sidor utan nya annonser och läser "
                f"max {SMART_MAX_PAGES} sidor per sport. Smart refresh läser bara ett gammalt prioriterat sidblock. "
                f"Läs nästa marknadsomgång fortsätter i block om {MARKET_BATCH_PAGES} sidor och sparar hela marknaden. "
                "Full genomsökning är endast för felsökning och kan vara tung på Streamlit Cloud."
            ),
        )
        mode = (
            "incremental" if mode_label == "Smart uppdatering"
            else "scheduled_refresh" if mode_label == "Smart refresh – bara gamla sidor"
            else "market_batch" if mode_label == "Läs nästa marknadsomgång"
            else "full"
        )
        single_category = st.selectbox(
            "Uppdatera endast en sport",
            list(CATEGORY_URLS.keys()),
            key="admin_category",
            help="Använd bara detta när du specifikt vill uppdatera en enda sport.",
        )

    st.caption(
        "**Uppdatera alla sporter** kör valt hämtläge för både hockey och fotboll. "
        "**Endast vald sport** gör samma sak men bara för sporten i rullistan. "
        "**Avbryt hämtning** stoppar en pågående körning utan att radera redan sparade annonser."
    )

    b1, b2, b3 = st.columns([2, 1, 1])
    with b1:
        if st.button(
            "Uppdatera alla sporter",
            type="primary",
            use_container_width=True,
            disabled=st.session_state["fetch_status"] == "running",
        ):
            start_fetch("__all__", headless, mode)
            st.rerun()

    with b2:
        if st.button(
            "Endast vald sport",
            use_container_width=True,
            disabled=st.session_state["fetch_status"] == "running",
        ):
            start_fetch(single_category, headless, mode)
            st.rerun()

    with b3:
        if st.button(
            "Avbryt hämtning",
            use_container_width=True,
            disabled=st.session_state["fetch_status"] != "running",
        ):
            stop_fetch()
            st.rerun()

    sync_cols = st.columns(2)
    for idx, category_name in enumerate(CATEGORY_URLS.keys()):
        sync = get_market_sync_status(category_name)
        sport_name = "Hockey" if "Hockey" in category_name else "Fotboll"
        with sync_cols[idx]:
            state_text = "KLAR" if sync["complete"] else f"nästa sida {sync['next_page']}"
            st.caption(f"📡 {sport_name}: {state_text} • inlästa sidor: {format_loaded_pages(sync['loaded_pages'])}")

    st.caption("**↺ Börja om full marknadsläsning** flyttar bara scannerns startpunkt tillbaka till sida 1. Den raderar inte annonser som redan finns sparade.")
    if st.button("↺ Börja om full marknadsläsning", use_container_width=True, disabled=st.session_state["fetch_status"] == "running"):
        reset_market_sync()
        st.success("Marknadsscannerns fortsättningspunkt är återställd. Sparade annonser är kvar.")

    with st.expander("Importera verifierade sålda comps"):
        st.caption(
            "CSV/JSON måste innehålla ett faktiskt sålt pris. FlipFynd gissar inte att en avslutad annons är såld "
            "och gissar inte valutakurser. För annan valuta än SEK krävs explicit SEK-pris eller fx_rate_to_sek."
        )
        sold_upload = st.file_uploader(
            "Välj CSV eller JSON",
            type=["csv", "json"],
            key="sold_comp_upload",
        )
        if sold_upload is not None:
            if st.button("Validera och importera comps", use_container_width=True):
                try:
                    rows = parse_import_bytes(sold_upload.getvalue(), sold_upload.name)
                    existing = load_sold_comps(str(SOLD_COMPS_PATH))
                    result = import_sold_comp_rows(
                        rows,
                        existing=existing,
                        provenance=f"manual_upload:{sold_upload.name}",
                    )
                    if result["added_count"]:
                        save_sold_comps(result["records"], SOLD_COMPS_PATH)
                        get_sold_comp_data.clear()
                        clear_analysis_cache()
                        st.session_state["result_cache"] = {}
                    st.success(
                        f"{result['added_count']} nya comps importerade • "
                        f"{result['duplicate_count']} dubbletter • {result['error_count']} avvisade rader."
                    )
                    if result["errors"]:
                        with st.expander("Visa avvisade rader"):
                            for err in result["errors"][:25]:
                                st.write(f"Rad {err['row']}: {err['error']}")
                except Exception as exc:
                    st.error(f"Importen kunde inte läsas: {exc}")

    with st.expander("Samla verifierade avslut"):
        st.caption(
            "Collector söker i redan inlästa lokala data men tar bara in objekt med explicit såld-evidens. "
            "En annons som bara är avslutad eller stängd räknas aldrig som såld."
        )
        current_sold = load_sold_comps(str(SOLD_COMPS_PATH))
        st.write(f"**{len(current_sold)} verifierade sold comps sparade i denna datamiljö.**")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Samla från inlästa annonser", use_container_width=True):
                try:
                    source_rows = get_data()
                    result = collect_sold_comps(
                        source_rows,
                        existing=current_sold,
                        source_name="tradera_loaded_data",
                    )
                    if result["added_count"]:
                        save_sold_comps(result["records"], SOLD_COMPS_PATH)
                        get_sold_comp_data.clear()
                        clear_analysis_cache()
                        st.session_state["result_cache"] = {}
                    st.success(
                        f"{result['added_count']} nya verifierade avslut • "
                        f"{result['duplicate_count']} dubbletter • "
                        f"{result['not_sold_count']} ignorerade eftersom såld-evidens saknades • "
                        f"{result['invalid_count']} ogiltiga."
                    )
                except Exception as exc:
                    st.error(f"Collector kunde inte köras: {exc}")
        with c2:
            export_payload = json.dumps(current_sold, ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button(
                "Exportera sold-comp-bibliotek",
                data=export_payload,
                file_name="flipfynd_sold_comps.json",
                mime="application/json",
                use_container_width=True,
                help="Spara en kopia av historiken. Streamlit Clouds lokala filsystem är inte permanent mellan alla omstarter/deploys.",
            )
        st.caption(
            "Viktigt: lagring i själva Streamlit-instansen är runtime-lagring. Exportfunktionen gör att sold-comp-historiken "
            "kan bevaras tills en extern persistent databas kopplas in."
        )

    with st.expander("Underhåll / riskzon"):
        st.warning("Dessa funktioner påverkar lokalt analysunderlag och cache.")
        r1, r2 = st.columns(2)
        with r1:
            if st.button("Rensa analys-cache", use_container_width=True):
                clear_analysis_cache()
                st.session_state["result_cache"] = {}
                st.success("Analys-cache rensad.")
        with r2:
            if st.button("Rensa all data", use_container_width=True):
                clear_all_loaded_data()
                clear_analysis_cache()
                get_data.clear()
                st.session_state["results"] = None
                st.session_state["result_cache"] = {}
                st.rerun()

    if st.session_state.get("debug"):
        with st.expander("Teknisk analysstatistik"):
            st.json(st.session_state["debug"])
