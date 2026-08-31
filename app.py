import hashlib
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

from src.analysis_cache import (
    build_analysis_signature,
    clear_analysis_cache,
    get_cached_analysis,
    set_cached_analysis,
)

from src.analyzer import (
    analyze_item,
)

from src.loader import (
    load_data,
)

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
)


st.set_page_config(
    page_title="FlipFynd",
    page_icon="🃏",
    layout="wide",
)


APP_VERSION = "v0.4.8"


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

DATA_PATH = (
    BASE_DIR
    / "tradera_data.json"
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

def get_data():
    return load_data(
        str(DATA_PATH)
    )


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
    try:
        stat = (
            DATA_PATH.stat()
        )

        raw = (
            f"{stat.st_mtime_ns}_"
            f"{stat.st_size}"
        )

    except FileNotFoundError:
        raw = "missing"

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
    command = [
        sys.executable,
        "fetch_tradera_pages.py",
        "--category",
        category,
        "--mode",
        mode,
        "--output",
        "tradera_data.json",
    ]

    if not headless:
        command.append(
            "--headed"
        )

    log_file = open(
        FETCH_LOG_PATH,
        "w",
        encoding="utf-8",
    )

    creationflags = 0

    if sys.platform.startswith(
        "win"
    ):
        creationflags = (
            subprocess
            .CREATE_NEW_PROCESS_GROUP
        )

    process = subprocess.Popen(
        command,
        stdout=log_file,
        stderr=
            subprocess.STDOUT,
        text=True,
        cwd=str(
            BASE_DIR
        ),
        creationflags=
            creationflags,
    )

    st.session_state[
        "fetch_process"
    ] = process

    st.session_state[
        "fetch_status"
    ] = "running"

    st.session_state[
        "fetch_category"
    ] = category

    st.session_state[
        "fetch_target_pages"
    ] = 0

    st.session_state[
        "fetch_last_message"
    ] = (
        f"Hämtar "
        f"{category}..."
    )


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
    debug = {
        "total_items":
            len(data),

        "after_sport":
            0,

        "after_search_price":
            0,

        "fast_candidates":
            0,

        "full_analysis":
            0,

        "cache_hits":
            0,

        "final_results":
            0,
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
            not isinstance(
                price,
                (
                    int,
                    float,
                ),
            )
            or price <= 0
        ):
            continue

        total_cost = total_acquisition_cost(
            price,
            item.get("frakt"),
        )

        if (
            total_cost is None
            or total_cost > max_price
        ):
            continue

        if not item_matches_search(
            item,
            search,
        ):
            continue

        debug[
            "after_search_price"
        ] += 1

        fast = analyze_item(
            item,
            mode="fast",
            strategy_mode=
                strategy,
            sport=sport,
        )

        if (
            sale_type
            == "Endast auktioner"
            and fast.get(
                "sale_type"
            )
            != "Auktion"
        ):
            continue

        if (
            sale_type
            == "Endast Köp nu"
            and fast.get(
                "sale_type"
            )
            != "Köp nu"
        ):
            continue

        if (
            numbered_only
            and not is_numbered(
                item
            )
        ):
            continue

        if (
            patch_only
            and not is_patch(
                item
            )
        ):
            continue

        if (
            auto_only
            and not is_auto(
                item
            )
        ):
            continue

        candidates.append(
            (
                item,
                fast,
            )
        )

    candidates.sort(
        key=lambda value: (
            value[1].get(
                "rank_score",
                0,
            ),
            value[1].get(
                "player_market_score",
                0,
            ),
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
                all_items=sport_items,
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
    .ff-hero {
        padding: 0.2rem 0 0.8rem 0;
    }
    .ff-hero h1 {
        margin-bottom: 0.15rem;
    }
    .ff-muted {
        color: #8b949e;
        font-size: 0.92rem;
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
    div[data-testid="stMetric"] {
        border: 1px solid rgba(128, 128, 128, 0.22);
        border-radius: 0.65rem;
        padding: 0.55rem 0.65rem;
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
      <h1>🃏 FlipFynd</h1>
      <div class="ff-muted">Hitta samlarkort med potential för vidareförsäljning – rankade efter pris, efterfrågan, säljsannolikhet och möjlig vinst.</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(f"{APP_VERSION} • Hockey + fotboll")

if st.session_state.get("fetch_last_message"):
    message = st.session_state["fetch_last_message"]
    if st.session_state.get("fetch_status") == "finished":
        st.success(message)
    elif st.session_state.get("fetch_status") == "failed":
        st.error(message)
    else:
        st.info(message)

if st.session_state.get("fetch_status") == "failed":
    log_tail = read_fetch_log_tail()
    if log_tail:
        with st.expander("Visa tekniska detaljer om hämtfelet"):
            st.code(log_tail, language="text")


data = get_data()
if not isinstance(data, list):
    data = []

st.subheader("Hitta fynd")
_fetch_state_summary = load_fetch_state()
_last_values = [
    info.get("last_fetch_at")
    for info in _fetch_state_summary.get("categories", {}).values()
    if info.get("last_fetch_at")
]
_latest_fetch = format_last_fetch_time(max(_last_values)) if _last_values else "Aldrig"
st.caption(
    (f"{len(data):,} annonser i analysunderlaget • senast uppdaterat {_latest_fetch}")
    .replace(",", " ")
)

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
        "🔎 Hitta fynd",
        type="primary",
        use_container_width=True,
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
        st.info(
            "Inga annonser matchar dina filter just nu. Prova en högre budget, lägre analyssäkerhet eller bredare sökning."
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
        expected = item.get("expected_resale", 0) or 0
        floor = item.get("floor_resale", 0) or 0
        best_case = item.get("best_case_resale", 0) or 0
        net_profit = item.get("net_profit_estimate", 0) or 0
        sale_probability = item.get("sale_probability", 0) or 0

        with st.container(border=True):
            st.markdown(f'<div class="ff-decision">#{index} · {decision_label}</div>', unsafe_allow_html=True)
            st.caption(decision_help)
            st.markdown(
                f'<div class="ff-card-title">{item.get("titel", "")}</div>',
                unsafe_allow_html=True,
            )

            m1, m2 = st.columns(2)
            with m1:
                st.metric("Köp för", f"{total_cost:.0f} kr")
            with m2:
                st.metric("Möjlig nettovinst", f"{net_profit:.0f} kr")

            m3, m4 = st.columns(2)
            with m3:
                if floor and expected and floor != expected:
                    resale_text = f"{floor:.0f}–{expected:.0f} kr"
                else:
                    resale_text = f"{expected:.0f} kr"
                st.metric("Realistiskt försäljningsvärde", resale_text)
            with m4:
                st.metric("Säljchans", f"{sale_probability:.0f} %")

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

            player_match_confidence = item.get("player_match_confidence", "low")
            if player_match_confidence == "medium":
                st.caption("⚠️ Spelarnamnet identifierades med stavningstolerans – kontrollera titeln före köp.")
            elif player_match_confidence == "low":
                st.caption("⚠️ Osäker spelaridentifiering. FlipFynd tillåter inte ett tydligt köpbeslut på den här träffen.")

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

                with d2:
                    st.write(f"**Försiktigt värde:** {floor:.0f} kr")
                    st.write(f"**Förväntat värde:** {expected:.0f} kr")
                    st.write(f"**Best case:** {best_case:.0f} kr")
                    st.write(f"**Riskjusterad vinst:** {item.get('risk_adjusted_profit', 0)} kr")
                    st.write(f"**ROI:** {item.get('roi_estimate', 0)}")
                    st.write(f"**Rank:** {item.get('rank_score', 0)}")

                reasons = item.get("reasons", [])
                if reasons:
                    st.write("**Varför rankas kortet så här?**")
                    for reason in reasons:
                        st.write(f"- {reason}")

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
        "Uppdatera Tradera-underlaget. FlipFynd går automatiskt sida för sida – du behöver inte välja antal sidor."
    )

    category = st.selectbox(
        "Sport/kategori att hämta",
        list(CATEGORY_URLS.keys()),
        key="admin_category",
    )

    info = fetch_state.get("categories", {}).get(category, {})
    last_fetch = format_last_fetch_time(info.get("last_fetch_at"))
    last_new = int(info.get("last_new_items", 0) or 0)
    last_pages = int(info.get("last_pages_scanned", 0) or 0)
    last_stop = info.get("last_stop_reason", "")

    st.write(f"**Senast uppdaterad:** {last_fetch}")
    if info.get("last_fetch_at"):
        st.caption(
            f"Senaste körningen: {last_pages} sidor genomsökta • {last_new} nya annonser"
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
            ["Smart uppdatering", "Full genomsökning"],
            key="admin_mode",
            help=(
                "Smart uppdatering börjar på sida 1 och stoppar efter tre hela sidor utan nya annonser. "
                "Full genomsökning fortsätter tills Tradera inte visar fler annonser, med en säkerhetsgräns på 250 sidor."
            ),
        )
        mode = "incremental" if mode_label == "Smart uppdatering" else "full"

    b1, b2 = st.columns(2)
    with b1:
        if st.button(
            "Uppdatera annonser",
            type="primary",
            use_container_width=True,
            disabled=st.session_state["fetch_status"] == "running",
        ):
            start_fetch(category, headless, mode)
            st.rerun()

    with b2:
        if st.button(
            "Avbryt hämtning",
            use_container_width=True,
            disabled=st.session_state["fetch_status"] != "running",
        ):
            stop_fetch()
            st.rerun()

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
