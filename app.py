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


APP_VERSION = "v0.2.2"


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
    pages,
    headless,
    mode,
):
    command = [
        sys.executable,
        "fetch_tradera_pages.py",
        "--category",
        category,
        "--pages",
        str(pages),
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
    ] = pages

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

        shipping = (
            item.get(
                "frakt"
            )
        )

        shipping = (
            0
            if shipping is None
            else shipping
        )

        if (
            price
            + shipping
            > max_price
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
                all_items=data,
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


st.title(
    "🃏 FlipFynd"
)

st.caption(
    f"{APP_VERSION} • Hitta undervärderade hockey- och fotbollskort för vidareförsäljning."
)


if st.session_state.get(
    "fetch_last_message"
):
    st.info(
        st.session_state[
            "fetch_last_message"
        ]
    )

if st.session_state.get("fetch_status") == "failed":
    log_tail = read_fetch_log_tail()
    if log_tail:
        with st.expander("Visa hämtfel"):
            st.code(log_tail, language="text")


fetch_state = (
    load_fetch_state()
)


with st.expander(
    "1. Hämta annonser",
    expanded=True,
):
    col1, col2, col3 = (
        st.columns(3)
    )

    with col1:
        category = (
            st.selectbox(
                "Sport/kategori",
                list(
                    CATEGORY_URLS.keys()
                ),
            )
        )

    info = (
        fetch_state.get(
            "categories",
            {},
        ).get(
            category,
            {},
        )
    )

    loaded_pages = (
        info.get(
            "loaded_pages",
            [],
        )
    )

    max_loaded = (
        info.get(
            "max_page_loaded",
            0,
        )
    )

    with col2:
        pages = st.selectbox(
            "Hämta upp till sida",
            list(
                range(
                    10,
                    101,
                    10,
                )
            ),
        )

    with col3:
        headless = (
            st.checkbox(
                "Kör i bakgrunden",
                value=True,
            )
        )

    mode_label = st.radio(
        "Hämtläge",
        [
            "Bygg vidare",
            "Börja om från sida 1",
        ],
    )

    mode = (
        "incremental"
        if mode_label
        == "Bygg vidare"
        else "full"
    )

    st.write(
        "**Inlästa sidor:** "
        + format_loaded_pages(
            loaded_pages
        )
    )

    if (
        mode == "incremental"
        and max_loaded
    ):
        st.caption(
            f"Nästa sida: "
            f"{max_loaded + 1}"
        )

    b1, b2, b3, b4 = (
        st.columns(4)
    )

    with b1:
        if st.button(
            "Hämta annonser",
            disabled=(
                st.session_state[
                    "fetch_status"
                ]
                == "running"
            ),
        ):
            start_fetch(
                category,
                pages,
                headless,
                mode,
            )

            st.rerun()

    with b2:
        if st.button(
            "Avbryt",
            disabled=(
                st.session_state[
                    "fetch_status"
                ]
                != "running"
            ),
        ):
            stop_fetch()

            st.rerun()

    with b3:
        if st.button(
            "Rensa analys-cache"
        ):
            clear_analysis_cache()

            st.session_state[
                "result_cache"
            ] = {}

            st.success(
                "Analys-cache rensad."
            )

    with b4:
        if st.button(
            "Rensa all data"
        ):
            clear_all_loaded_data()

            clear_analysis_cache()

            get_data.clear()

            st.session_state[
                "results"
            ] = None

            st.session_state[
                "result_cache"
            ] = {}

            st.rerun()


data = get_data()

if not isinstance(
    data,
    list,
):
    data = []


st.write(
    f"**Objekt i datafil:** "
    f"{len(data)}"
)


with st.form(
    "analysis_form"
):
    c1, c2, c3, c4 = (
        st.columns(4)
    )

    with c1:
        sport_label = (
            st.selectbox(
                "Analysera",
                [
                    "Hockey",
                    "Fotboll",
                ],
            )
        )

        sport = (
            "hockey"
            if sport_label
            == "Hockey"
            else "football"
        )

    with c2:
        search = (
            st.text_input(
                "Sökord",
                value="",
            )
        )

    with c3:
        max_price = (
            st.number_input(
                "Maxpris inkl. frakt",
                min_value=0,
                value=1000,
                step=10,
            )
        )

    with c4:
        show_count = (
            st.number_input(
                "Antal att visa",
                min_value=1,
                max_value=200,
                value=20,
            )
        )

    c5, c6, c7 = (
        st.columns(3)
    )

    with c5:
        sale_type = (
            st.selectbox(
                "Annonsform",
                [
                    "Alla",
                    "Endast auktioner",
                    "Endast Köp nu",
                ],
            )
        )

    with c6:
        full_limit = (
            st.selectbox(
                "Djupanalys topp",
                list(
                    range(
                        1,
                        21,
                    )
                ),
                index=9,
            )
        )

    with c7:
        strategy_label = (
            st.selectbox(
                "Läge",
                [
                    "Quick flip",
                    "Premium flip",
                    "Kortläge",
                ],
            )
        )

    strategy_map = {
        "Quick flip":
            "quick_flip",

        "Premium flip":
            "premium_flip",

        "Kortläge":
            "kort",
    }

    strategy = (
        strategy_map[
            strategy_label
        ]
    )

    f1, f2, f3 = (
        st.columns(3)
    )

    with f1:
        numbered_only = (
            st.checkbox(
                "Endast numrerade",
                value=False,
            )
        )

    with f2:
        patch_only = (
            st.checkbox(
                "Endast patch/relic",
                value=False,
            )
        )

    with f3:
        auto_only = (
            st.checkbox(
                "Endast autograf",
                value=False,
            )
        )

    display1, display2 = (
        st.columns(2)
    )

    with display1:
        minimum_confidence = (
            st.slider(
                "Minsta säkerhet",
                0.0,
                1.0,
                0.0,
                0.05,
            )
        )

    with display2:
        show_skip = (
            st.checkbox(
                "Visa även SKIP",
                value=True,
            )
        )

    run = (
        st.form_submit_button(
            "Visa fynd",
            type="primary",
        )
    )


if run:
    with st.spinner(
        f"Analyserar "
        f"{sport_label.lower()}..."
    ):
        (
            results,
            debug,
        ) = analyze_data(
            data=data,
            sport=sport,
            search=search,
            max_price=
                max_price,
            sale_type=
                sale_type,
            full_limit=
                full_limit,
            strategy=
                strategy,
            numbered_only=
                numbered_only,
            patch_only=
                patch_only,
            auto_only=
                auto_only,
        )

    st.session_state[
        "results"
    ] = results

    st.session_state[
        "debug"
    ] = debug


if st.session_state.get(
    "debug"
):
    with st.expander(
        "Felsökningsstatistik"
    ):
        st.json(
            st.session_state[
                "debug"
            ]
        )


if st.session_state.get(
    "results"
) is not None:

    filtered = []

    for item in (
        st.session_state[
            "results"
        ]
    ):
        if (
            item.get(
                "confidence",
                0,
            )
            < minimum_confidence
        ):
            continue

        if (
            not show_skip
            and item.get(
                "beslut"
            )
            == "SKIP"
        ):
            continue

        filtered.append(
            item
        )

    st.subheader(
        f"Resultat: "
        f"{len(filtered)}"
    )

    for index, item in enumerate(
        filtered[
            :show_count
        ],
        start=1,
    ):
        with st.container(
            border=True
        ):
            st.markdown(
                f"### #{index} – "
                f"{item.get('titel', '')}"
            )

            a, b, c, d = (
                st.columns(4)
            )

            with a:
                st.write(
                    f"**Pris:** "
                    f"{item.get('pris', 0)} kr"
                )

                st.write(
                    f"**Frakt:** "
                    f"{item.get('frakt')} kr"
                )

                st.write(
                    f"**Total:** "
                    f"{item.get('total_cost', 0)} kr"
                )

            with b:
                st.write(
                    f"**Spelare:** "
                    f"{item.get('player_name') or 'Okänd'}"
                )

                st.write(
                    f"**Spelarscore:** "
                    f"{item.get('player_market_score', 0)}/100"
                )

                st.write(
                    f"**Efterfrågan:** "
                    f"{item.get('demand_tier', '')}"
                )

            with c:
                st.write(
                    f"**Beslut:** "
                    f"{item.get('beslut', '')}"
                )

                st.write(
                    f"**Rank:** "
                    f"{item.get('rank_score', 0)}"
                )

                st.write(
                    f"**Säljchans:** "
                    f"{item.get('sale_probability', 0)} %"
                )

            with d:
                st.write(
                    f"**Riskjusterad vinst:** "
                    f"{item.get('risk_adjusted_profit', 0)} kr"
                )

                st.write(
                    f"**Exit:** "
                    f"{item.get('exit_speed', '')}"
                )

                st.write(
                    f"**Säljare:** "
                    f"{get_seller(item)}"
                )

            if item.get(
                "kommentar"
            ):
                st.write(
                    f"**Kommentar:** "
                    f"{item['kommentar']}"
                )

            if item.get(
                "lank"
            ):
                st.markdown(
                    f"[Öppna annons]"
                    f"({item['lank']})"
                )

            with st.expander(
                "Värde och vinst"
            ):
                st.write(
                    f"Förväntat värde: "
                    f"**{item.get('expected_resale', 0)} kr**"
                )

                st.write(
                    f"Försiktigt värde: "
                    f"**{item.get('floor_resale', 0)} kr**"
                )

                st.write(
                    f"Best case: "
                    f"**{item.get('best_case_resale', 0)} kr**"
                )

                st.write(
                    f"Nettovinst: "
                    f"**{item.get('net_profit_estimate', 0)} kr**"
                )

                st.write(
                    f"ROI: "
                    f"**{item.get('roi_estimate', 0)}**"
                )

            with st.expander(
                "Varför rankas kortet så?"
            ):
                for reason in (
                    item.get(
                        "reasons",
                        [],
                    )
                ):
                    st.write(
                        f"- {reason}"
                    )

                if item.get(
                    "risk_flags"
                ):
                    st.write(
                        "**Risker:**"
                    )

                    for risk in (
                        item.get(
                            "risk_flags",
                            [],
                        )
                    ):
                        st.write(
                            f"- {risk}"
                        )