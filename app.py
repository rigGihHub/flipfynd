import hashlib
import json
import re
import subprocess
import sys
import os
import time
from pathlib import Path
from src.player_knowledge import knowledge_coverage
from src.card_explanation import build_card_explanation, build_card_identity_summary
from src.card_parser import parse_card_features


import streamlit as st
import streamlit.components.v1 as components

try:
    from streamlit_autorefresh import (
        st_autorefresh
    )
except ImportError:
    st_autorefresh = None

from src.adaptive_deepening import select_adaptive_full_analysis_indices, dynamic_deep_analysis_cap
from src.candidate_coverage import diversify_full_analysis_indices
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
try:
    from src.sold_comp_collector import collect_sold_comps, smart_collect_local_sold_comps
except ImportError:
    # Deployment compatibility guard: a partial/stale deploy must not crash the entire app.
    # collect_sold_comps existed before smart_collect_local_sold_comps was introduced.
    from src.sold_comp_collector import collect_sold_comps
    smart_collect_local_sold_comps = None
from src.external_sold_sources import available_adapters, import_external_sold_rows
from src.sold_source_registry import sold_source_registry, source_readiness_summary
from src.comp_source_intelligence import build_comp_research_plan
from src.seller_bundle_opportunity import find_same_seller_listings, build_shared_shipping_scenario, classify_same_seller_addon, build_best_same_seller_basket
from src.seller_identity import recover_seller_from_market
from src.multi_source_comp_consensus import build_multi_source_consensus
from src.comp_acquisition_router import build_comp_acquisition_router
from src.comp_research_workbench import build_research_links, fetch_sportscardspro_context, sportscardspro_api_configured, parse_verified_sales_batch
from src.sold_comp_quality import audit_sold_comp_records
from src.sold_comp_intake import sold_comp_intake_audit
from src.sold_gap_planner import build_sold_research_queue
from src.sold_research_assist import build_exact_research_query, ebay_sold_search_url, build_manual_sold_row, build_quick_capture_defaults, research_progress
from src.sold_acquisition_pipeline import acquire_sold_batch
from src.visual_detective import analyze_listing_images
from src.visual_oddity_detector import build_visual_oddity_signal
from src.reference_image_verification import verify_against_reference_traits
from src.visual_identity import build_visual_card_candidates
from src.visual_checklist_match import match_visual_to_checklist_knowledge
from src.visual_exact_identity import resolve_visual_exact_identity
from src.exact_comp_hunter import hunt_exact_comps
from src.comp_evidence_ladder import build_exact_evidence_ladder, build_premium_evidence_ladder
from src.comp_verdict import build_comp_verdict
from src.comp_quality_guard import build_comp_quality_guard
from src.evidence_scenario_range import build_evidence_scenario_range
from src.dynamic_max_bid import build_dynamic_max_bid
from src.exact_identity_gate import build_exact_identity_gate
from src.buy_now_hunter import build_buy_now_opportunity
from src.ending_soon_hunter import build_ending_soon_opportunity
from src.find_diagnostics import summarize_no_find_reasons
from src.finding_funnel_diagnostic import build_finding_funnel_diagnostic
from src.find_more_cards import select_second_pass_indices
from src.discovery_engine import build_discovery_map, select_discovery_indices
from src.market_sweep_engine import build_market_sweep_map, select_market_sweep_indices
from src.budget_discovery_coverage import add_budget_coverage_indices, budget_coverage_summary
from src.segment_discovery_coverage import add_segment_coverage_indices, segment_coverage_summary
from src.segment_yield_learning import build_segment_yield_report, best_observed_segments
from src.decision_tiers import build_decision_tiers
from src.decision_tiers_compat import build_decision_tiers_compat
from src.opportunity_top5 import build_opportunity_top5
from src.research_shortlist import build_research_shortlist, evidence_coverage, research_identity_failure_diagnostics
from src.unlock_research_queue import build_unlock_research_queue
from src.auto_comp_research import run_auto_comp_research
from src.market_gap_hunter import build_market_gap_queue
from src.active_supply_intelligence import verify_active_supply, classify_verified_supply
from src.exact_card_supply import build_exact_supply_query, count_analyzed_exact_matches, verify_exact_query_supply, exact_identity_key
from src.exact_supply_confirmation import build_confirmation_report
from src.exact_supply_history import build_snapshot, load_history, save_snapshot, summarize_history
from src.supply_vs_sales_monitor import build_supply_vs_sales_monitor
from src.market_pressure_monitor import build_market_pressure_monitor
from src.pressure_research_queue import build_pressure_research_queue
from src.pressure_research_drilldown import build_pressure_drilldown
from src.research_action_center import build_research_actions, build_low_click_action_plan
from src.automatic_research_flow import build_automatic_research_flow
from src.mispricing_detector import build_mispricing_review_queue
from src.bad_listing_hunter import build_bad_listing_queue
from src.oddity_registry import registry_stats
from src.oddity_registry_learning import build_registry_proposal_queue
from src.oddity_story_hunter import build_oddity_story_queue
from src.lot_treasure_hunter import build_lot_treasure_queue
from src.search_expansion import build_search_expansion_plan, tradera_api_readiness
from src.tradera_api_search import run_search_plan, save_expansion_items
from src.tradera_seller_inventory import discover_active_seller_inventory
from src.public_seller_inventory import fetch_public_seller_inventory_batch
from src.seller_live_quick_analysis import quick_analyze_seller_inventory
from src.fast_analysis_pool import select_fast_analysis_pool
from src.card_listing_integrity import assess_listing_integrity
from src.analysis_budget import fast_analysis_budget
from src.search_run_cache import build_search_run_signature, get_reusable_search, store_reusable_search
from src.ordinary_analysis_pipeline_v2 import analyze_data as shared_analyze_data
from src.persistent_search_jobs import available as jobs_available, create_job, latest_active_job, latest_completed_job
from src.ordinary_search_job_contract import build_ordinary_search_job_payload, unpack_completed_ordinary_job
from src.persistent_store import load_namespace as load_persistent_namespace, save_namespace as save_persistent_namespace
from src.latest_market import LATEST_MAX_PAGES, latest_analysis_items
from src.seller_live_full_analysis import full_analyze_live_seller_item
from src.seller_top5 import build_seller_top5, seller_result_tier
from src.asking_price_ui import render_asking_price_opportunity, render_asking_price_shortlist
from src.collector_signal_coverage import add_collector_signal_coverage_indices
from src.seller_top5_controller import reset_seller_top5_search, resolve_seller_top5
from src.seller_inventory_triage import build_seller_inventory_triage
from src.search_yield_learning import build_yield_report, route_budget_guidance
from src.near_buy_guidance import build_near_buy_guidance
from src.detail_evidence_fusion import build_detail_evidence_fusion
from src.flip_journal import (
    build_entry_from_listing, journal_metrics, load_journal, save_journal, update_entry,
)
from src.outcome_calibration import build_outcome_calibration
from src.calibration_miss_analysis import build_miss_analysis
from src.outcome_review import OUTCOME_REVIEW_REASONS, build_outcome_review_patch
from src.calibration_dashboard import build_calibration_dashboard
from src.false_positive_review import build_false_positive_review
from src.false_negative_review import build_false_negative_review
from src.model_review_dashboard import build_model_review_dashboard
from src.persistent_store import (
    load_namespace, migrate_namespace_if_empty, save_namespace, storage_status,
)
from src.pending_sync import clear_pending, get_pending, pending_summary, record_pending


from src.shipping_truth import resolve_shipping
from src.pricing import (
    DEFAULT_UNKNOWN_SHIPPING,
    normalize_shipping,
    total_acquisition_cost,
)

from src import tradera_fetcher as _tradera_fetcher
from src.fetcher_compat import build_fetcher_api
from src.budget_portfolio import build_budget_portfolio
from src.portfolio_downside_stress import build_portfolio_downside_stress
from src.portfolio_opportunity_cost import build_portfolio_opportunity_cost
from src.portfolio_concentration import build_portfolio_concentration
from src.portfolio_identity_integrity import build_portfolio_identity_integrity
from src.player_momentum import build_player_momentum, build_starshot_watchlist
from src.momentum_source_intake import ingest_momentum_records
from src.momentum_source_registry import source_registry
from src.momentum_card_bridge import bridge_momentum_to_cards
from src.starshot_radar import build_starshot_radar
from src.prediction_outcome_validation import build_prediction_outcome_validation
from src.capital_efficiency_validation import build_capital_efficiency_validation
from src.error_segmentation import build_error_segmentation
from src.model_correction_candidates import build_model_correction_candidates
from src.correction_simulator import build_correction_simulation
from src.holdout_validation import build_holdout_validation
from src.correction_approval_gate import build_correction_approval_gate
from src.best_buy_decision_card import build_best_buy_decision_card
from src.top_buy_queue import build_top_buy_queue
from src.top_buy_decision_compare import build_top_buy_decision_compare
from src.buy_queue_risk_reward import build_queue_risk_reward
from src.buy_decision_summary import build_buy_decision_summary
from src.buy_now_vs_wait import build_queue_buy_timing
from src.price_drop_target import build_queue_price_drop_targets
from src.buy_opportunity_gap import build_queue_opportunity_gaps
from src.watch_priority import build_watch_priority_queue
from src.simple_card_language import sold_evidence_text, identity_text, sellability_text
from src.novice_navigation import (
    build_buy_view, build_ending_soon_view, build_watch_view, build_research_view, build_best_available_view,
)

_FETCHER = build_fetcher_api(_tradera_fetcher)
CATEGORY_URLS = _FETCHER.CATEGORY_URLS
clear_all_loaded_data = _FETCHER.clear_all_loaded_data
format_loaded_pages = _FETCHER.format_loaded_pages
load_fetch_state = _FETCHER.load_fetch_state
prune_active_items = _FETCHER.prune_active_items
reconcile_market_state_with_items = _FETCHER.reconcile_market_state_with_items
SMART_MAX_PAGES = _FETCHER.SMART_MAX_PAGES
MAX_ACTIVE_ITEMS_PER_CATEGORY = _FETCHER.MAX_ACTIVE_ITEMS_PER_CATEGORY
MARKET_BATCH_PAGES = _FETCHER.MARKET_BATCH_PAGES
get_market_sync_status = _FETCHER.get_market_sync_status
get_market_coverage_status = _FETCHER.get_market_coverage_status
get_smart_refresh_plan = _FETCHER.get_smart_refresh_plan
reset_market_sync = _FETCHER.reset_market_sync


st.set_page_config(
    page_title="FlipFynd",
    page_icon="🃏",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Streamlit can restore an open sidebar from the browser even when the app asks
# for a collapsed initial state. On narrow screens that hides the entire main
# app. Normalize that restored state once per new app session; later user opens
# are left alone.
if not st.session_state.get("_mobile_sidebar_normalized_v0147", False):
    components.html(
        """
        <script>
        (() => {
          let attempts = 0;
          const closeRestoredMobileSidebar = () => {
            attempts += 1;
            const parentDoc = window.parent.document;
            if (window.parent.innerWidth > 768) return;
            const sidebar = parentDoc.querySelector('[data-testid="stSidebar"]');
            const closeButton = sidebar && sidebar.querySelector('button[data-testid="stBaseButton-headerNoPadding"]');
            if (closeButton && closeButton.textContent.includes('keyboard_double_arrow_left')) {
              closeButton.click();
              return;
            }
            if (attempts < 20) window.setTimeout(closeRestoredMobileSidebar, 100);
          };
          closeRestoredMobileSidebar();
        })();
        </script>
        """,
        height=0,
        width=0,
    )
    st.session_state["_mobile_sidebar_normalized_v0147"] = True

# Futuristic trading-terminal skin: visual only, no decision semantics.
st.markdown("""
<style>
:root {
  --ff-grid: rgba(255,255,255,.025);
  --ff-panel: rgba(17,22,28,.78);
  --ff-line: rgba(226,164,92,.28);
  --ff-glow: rgba(226,164,92,.10);
}
.stApp {
  background:
    linear-gradient(var(--ff-grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--ff-grid) 1px, transparent 1px),
    radial-gradient(circle at 78% 8%, var(--ff-glow), transparent 28%);
  background-size: 32px 32px, 32px 32px, auto;
}
[data-testid="stMetric"], [data-testid="stExpander"], div[data-testid="stVerticalBlockBorderWrapper"] {
  background: linear-gradient(145deg, rgba(23,29,36,.82), rgba(12,16,21,.74));
  border: 1px solid var(--ff-line);
  box-shadow: 0 10px 32px rgba(0,0,0,.20), inset 0 1px rgba(255,255,255,.025);
  border-radius: 14px;
}
[data-testid="stMetric"] {
  position: relative;
  overflow: hidden;
}
[data-testid="stMetric"]::before {
  content: "";
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 2px;
  background: linear-gradient(180deg, transparent, rgba(226,164,92,.85), transparent);
}
h1, h2, h3 {
  letter-spacing: .025em;
}
button[kind="primary"], .stButton > button {
  border-radius: 10px;
  border: 1px solid rgba(226,164,92,.40);
  backdrop-filter: blur(8px);
}
div[data-testid="stCaptionContainer"] {
  opacity: .86;
}
@media (max-width: 640px) {
  .stApp { background-size: 24px 24px, 24px 24px, auto; }
  [data-testid="stSidebar"] {
    width: min(92vw, 420px) !important;
    min-width: min(92vw, 420px) !important;
  }
  [data-testid="stSidebar"] > div:first-child {
    width: min(92vw, 420px) !important;
  }
  [data-testid="stMetric"], [data-testid="stExpander"], div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 10px;
  }
  [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {
    line-height: 1.35;
  }
}
</style>
""", unsafe_allow_html=True)



APP_VERSION = "v0.14.35"

FETCH_SCOPE_MAP = {
    "🏒 Hockey": "Hockey - NHL",
    "⚽ Fotboll": "Fotboll",
    "🏒⚽ Båda": "__all__",
}

def selected_fetch_category(scope_label):
    return FETCH_SCOPE_MAP.get(scope_label, "__all__")

def fetch_scope_display(scope_label):
    return {
        "🏒 Hockey": "Hockey",
        "⚽ Fotboll": "Fotboll",
        "🏒⚽ Båda": "båda sporterna",
    }.get(scope_label, "båda sporterna")


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

DATA_PATH = (
    BASE_DIR
    / "tradera_data.json"
)

SEARCH_EXPANSION_DATA_PATH = (
    BASE_DIR
    / "data"
    / "search_expansion_items.json"
)

SOLD_COMPS_PATH = (
    BASE_DIR
    / "data"
    / "sold_comps.json"
)

FLIP_JOURNAL_PATH = BASE_DIR / "data" / "flip_journal.json"
PENDING_SYNC_PATH = BASE_DIR / "data" / "pending_sync.json"
EXACT_SUPPLY_HISTORY_PATH = BASE_DIR / "data" / "exact_supply_history.json"




def _resolve_tradera_api_credentials():
    """Resolve app-only Tradera credentials without exposing them in UI/logs."""
    app_id = os.getenv("TRADERA_APP_ID")
    app_key = os.getenv("TRADERA_APP_KEY")
    try:
        app_id = app_id or st.secrets.get("TRADERA_APP_ID")
        app_key = app_key or st.secrets.get("TRADERA_APP_KEY")
    except Exception:
        pass
    app_id = str(app_id or "").strip()
    app_key = str(app_key or "").strip()
    if not app_id or not app_key:
        return None
    return app_id, app_key

def _resolve_database_url():
    """Read a PostgreSQL URL without making it mandatory for local development."""
    for key in ("FLIPFYND_DATABASE_URL", "DATABASE_URL"):
        value = os.getenv(key)
        if value:
            return value
    try:
        for key in ("FLIPFYND_DATABASE_URL", "DATABASE_URL"):
            value = st.secrets.get(key)
            if value:
                return str(value)
        database = st.secrets.get("database")
        if database and database.get("url"):
            return str(database.get("url"))
    except Exception:
        pass
    return None


DATABASE_URL = _resolve_database_url()


@st.cache_data(ttl=60, show_spinner=False)
def _cached_storage_probe(database_url):
    return probe_database(database_url)


def _record_storage_error(area, exc):
    try:
        st.session_state[f"storage_error_{area}"] = str(exc)
    except Exception:
        pass


def _clear_storage_error(area):
    try:
        st.session_state.pop(f"storage_error_{area}", None)
    except Exception:
        pass


def _retry_pending_sync():
    """Retry complete pending namespace snapshots. Never performs a merge."""
    if not DATABASE_URL:
        return {"synced": [], "failed": [], "remaining": pending_summary(PENDING_SYNC_PATH)["count"]}
    result = {"synced": [], "failed": []}
    summary = pending_summary(PENDING_SYNC_PATH)
    area_by_namespace = {"sold_comps": "sold_comps", "flip_journal": "flip_journal"}
    for entry in summary["entries"]:
        namespace = entry.get("namespace")
        if not namespace:
            continue
        try:
            save_namespace(DATABASE_URL, namespace, entry.get("payload"))
            clear_pending(PENDING_SYNC_PATH, namespace)
            area = area_by_namespace.get(namespace)
            if area:
                _clear_storage_error(area)
            result["synced"].append(namespace)
        except Exception as exc:
            _record_storage_error(area_by_namespace.get(namespace, "status"), exc)
            result["failed"].append(namespace)
    result["remaining"] = pending_summary(PENDING_SYNC_PATH)["count"]
    return result


def _load_sold_comp_records():
    local_rows = load_sold_comps(str(SOLD_COMPS_PATH))
    pending = get_pending(PENDING_SYNC_PATH, "sold_comps")
    if pending is not None:
        payload = pending.get("payload")
        return [row for row in payload if isinstance(row, dict)] if isinstance(payload, list) else local_rows
    if not DATABASE_URL:
        return local_rows
    try:
        migrate_namespace_if_empty(DATABASE_URL, "sold_comps", local_rows)
        rows = load_namespace(DATABASE_URL, "sold_comps", [])
        _clear_storage_error("sold_comps")
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    except Exception as exc:
        _record_storage_error("sold_comps", exc)
        return local_rows


def _save_sold_comp_records(records):
    rows = list(records)
    if DATABASE_URL:
        try:
            save_namespace(DATABASE_URL, "sold_comps", rows)
            clear_pending(PENDING_SYNC_PATH, "sold_comps")
            _clear_storage_error("sold_comps")
            return "database"
        except Exception as exc:
            _record_storage_error("sold_comps", exc)
            record_pending(PENDING_SYNC_PATH, "sold_comps", rows, error=str(exc))
    save_sold_comps(rows, SOLD_COMPS_PATH)
    return "local"


def _load_flip_journal_records():
    local_rows = load_journal(FLIP_JOURNAL_PATH)
    pending = get_pending(PENDING_SYNC_PATH, "flip_journal")
    if pending is not None:
        payload = pending.get("payload")
        rows = payload.get("entries", []) if isinstance(payload, dict) else payload
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else local_rows
    if not DATABASE_URL:
        return local_rows
    try:
        migrate_namespace_if_empty(DATABASE_URL, "flip_journal", {"schema_version": 1, "entries": local_rows})
        payload = load_namespace(DATABASE_URL, "flip_journal", {"schema_version": 1, "entries": []})
        _clear_storage_error("flip_journal")
        rows = payload.get("entries", []) if isinstance(payload, dict) else payload
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    except Exception as exc:
        _record_storage_error("flip_journal", exc)
        return local_rows


def _save_flip_journal_records(entries):
    rows = list(entries)
    payload = {"schema_version": 1, "entries": rows}
    if DATABASE_URL:
        try:
            save_namespace(DATABASE_URL, "flip_journal", payload)
            clear_pending(PENDING_SYNC_PATH, "flip_journal")
            _clear_storage_error("flip_journal")
            return "database"
        except Exception as exc:
            _record_storage_error("flip_journal", exc)
            record_pending(PENDING_SYNC_PATH, "flip_journal", payload, error=str(exc))
    save_journal(rows, FLIP_JOURNAL_PATH)
    return "local"

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
    base = load_data(str(DATA_PATH))
    # Streamlit Cloud's local filesystem is replaced on every deployment.
    # Restore the last successfully fetched market before showing an empty app.
    if not base and DATABASE_URL:
        try:
            persisted = load_namespace(DATABASE_URL, "active_market", [])
            if isinstance(persisted, list):
                base = [row for row in persisted if isinstance(row, dict)]
                if base:
                    _clear_storage_error("active_market")
        except Exception as exc:
            _record_storage_error("active_market", exc)
    expansion = load_data(str(SEARCH_EXPANSION_DATA_PATH))
    merged = []
    seen = set()
    for item in list(base or []) + list(expansion or []):
        if not isinstance(item, dict):
            continue
        key = item.get("tradera_item_id") or item.get("lank") or item.get("url")
        if key:
            marker = str(key)
            if marker in seen:
                continue
            seen.add(marker)
        merged.append(item)
    return merged


@st.cache_data(show_spinner=False)
def get_sold_comp_data():
    return _load_sold_comp_records()


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


def item_matches_search(item, search):
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


def normalize_sport_category_search(search, sport):
    """Treat category words as 'all cards in selected sport', not keywords."""
    normalized = normalize_text(search)
    aliases = {
        "football": {"fotbollskort", "fotbolls kort", "football cards", "soccer cards"},
        "hockey": {"hockeykort", "hockey cards"},
    }
    return "" if normalized in aliases.get(str(sport or "").casefold(), set()) else search


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
            env={
                **os.environ,
                **({"FLIPFYND_DATABASE_URL": DATABASE_URL} if DATABASE_URL else {}),
            },
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

    # A new market fetch invalidates the old analysis immediately. Keeping
    # previous debug/results visible while fresh listings are loading makes two
    # different datasets look like one search (for example 240 current listings
    # next to diagnostics from an older 3,085-row run).
    st.session_state["results"] = None
    st.session_state["debug"] = None
    st.session_state["result_cache"] = {}
    st.session_state.pop("results_data_version", None)
    st.session_state.pop("last_completed_search_signature", None)
    st.session_state.pop("active_search_job_id", None)
    st.session_state["results_stale_notice"] = True

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
        # Defensive second invalidation: the fetched file may change after the
        # subprocess exits, so no pre-fetch diagnostics may survive completion.
        st.session_state["results"] = None
        st.session_state["debug"] = None
        st.session_state.pop("results_data_version", None)
        st.session_state.pop("last_completed_search_signature", None)
        st.session_state["results_stale_notice"] = True

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
    """Return True only for a real autograph signal, using all listing text we have.

    The canonical parser deliberately does not treat a bare word like "Signature"
    as proof of an autograph; names such as Signature Style and Silver Script are
    product/parallel names and caused false positives in the old filter.
    """
    combined = " ".join(
        str(item.get(key) or "")
        for key in ("titel", "title", "raw_text", "full_description", "description")
    )
    return bool(parse_card_features(combined).get("is_auto"))



@st.cache_data(show_spinner=False, max_entries=6000)
def _cached_fast_analysis(item_signature, item, sport, strategy):
    """Reuse the shared worker-safe first-pass analysis across reruns."""
    return analyze_item(item, mode="fast", strategy_mode=strategy, sport=sport)


def _fast_signature(item, sport, strategy):
    payload = {
        "url": item.get("url") or item.get("link"),
        "title": item.get("titel") or item.get("title"),
        "price": item.get("pris"), "shipping": item.get("frakt"),
        "raw_text": item.get("raw_text"),
        "full_description": item.get("full_description"),
        "sport": sport, "strategy": strategy,
    }
    return hashlib.sha1(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()

def _cached_seller_analysis(item, *, all_items=None, mode="fast", strategy_mode="quick_flip", sport="hockey"):
    """Share both analysis caches with the incremental seller workflow."""
    if mode == "fast":
        return _cached_fast_analysis(
            _fast_signature(item, sport, strategy_mode),
            item,
            sport,
            strategy_mode,
        )

    inventory_size = len(all_items or [])
    signature = build_analysis_signature(
        item,
        data_size=inventory_size,
        mode=f"seller_{sport}_{strategy_mode}",
    )
    cached = get_cached_analysis(signature)
    if cached:
        return cached
    result = analyze_item(
        item,
        all_items=all_items,
        mode=mode,
        strategy_mode=strategy_mode,
        sport=sport,
    )
    set_cached_analysis(signature, result)
    return result



def analyze_data(*args, **kwargs):
    """Compatibility wrapper: UI and worker now share one analysis pipeline."""
    kwargs.setdefault("data_version", get_data_version())
    kwargs.setdefault("sold_comp_data", get_sold_comp_data())
    return shared_analyze_data(*args, **kwargs)


ensure_state()
update_fetch_status()

# Restore the last completed ordinary search when Streamlit creates a new
# browser session (for example after leaving the app and returning). Session
# state is ephemeral; the completed result is not.
if st.session_state.get("results") is None and DATABASE_URL:
    try:
        restored = load_persistent_namespace(DATABASE_URL, "ordinary_last_completed", {})
        if isinstance(restored, dict) and isinstance(restored.get("results"), list):
            st.session_state["results"] = restored.get("results") or []
            st.session_state["debug"] = restored.get("debug") if isinstance(restored.get("debug"), dict) else {}
            st.session_state["last_completed_search_signature"] = restored.get("signature")
            # Do not stamp the current data version here: the normal stale-data
            # guard must still invalidate restored results after a real market refresh.
            st.session_state["restored_completed_search"] = True
    except Exception:
        pass

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
st.markdown(f'<div class="ff-status-strip">{APP_VERSION} &nbsp;•&nbsp; HOCKEY / FOTBOLL &nbsp;•&nbsp; TRADERA SCANNER</div>', unsafe_allow_html=True)

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

# FlipFynd har en huvuduppgift: visa de bästa fynden just nu.
# Slutar snart/bevakning/research finns kvar som analysmotorer i bakgrunden,
# men användaren ska inte behöva välja arbetsläge innan fyndjakten.
_main_view = "Vad ska jag köpa?"
_advanced_terminal = st.checkbox(
    "Visa fördjupad analys",
    value=False,
    help="Öppnar hela analysterminalen med interna mått, jämförelser, kapitalverktyg och administration.",
    key="show_advanced_terminal",
)
if not _advanced_terminal:
    st.caption("Enkel vy · avancerade poäng och metoddetaljer är dolda tills du ber om dem.")

st.subheader("Vad ska jag köpa?")
if repaired_categories:
    st.info(
        "🧭 Marknadstäckningen har rättats för "
        + ", ".join(repaired_categories)
        + ". Gammal sidstatus stämde inte med annonslänkarna och har därför byggts om från verifierad data."
    )
if st.session_state.pop("results_stale_notice", False):
    st.caption("🔄 Annonsdata ändrades efter din förra sökning. Det gamla sökresultatet rensades så att du inte ser en inaktuell nolla.")
if st.session_state.pop("restored_completed_search", False):
    st.caption("↩️ Din senaste färdiga fyndsökning har återställts.")
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

# Legacy rows without a source category are not a usable market snapshot.
# After "Rensa huvudsökning" they must not appear as 2 845 live listings.
_visible_data = [item for item in data if infer_item_sport(item) in ("hockey", "football")]
_sport_counts = {"hockey": 0, "football": 0, "unknown": 0}
for _item in _visible_data:
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

# Distinguish the full saved archive from the current latest-scan window.
# Repeated latest refreshes are expected to overlap heavily and therefore do
# not necessarily increase the archive by many rows.
_total_loaded = len(_visible_data)
_latest_window = latest_analysis_items(_visible_data)
_latest_window_count = len(_latest_window)

st.caption(
    (
        f"Totalt inlästa: {_total_loaded:,} annonser • "
        + " • ".join(_count_parts)
        + f" • aktuell senaste-scan: {_latest_window_count:,} • {_latest_label} {_latest_fetch}"
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

fetch_scope = st.radio(
    "Sport att uppdatera",
    list(FETCH_SCOPE_MAP.keys()),
    index=0,
    horizontal=True,
    key="onboarding_fetch_scope",
)
fetch_category = selected_fetch_category(fetch_scope)
if st.button(
    "🔄 Uppdatera och läs in fler annonser" if _has_data else "📥 Läs in annonser",
    type="primary",
    use_container_width=True,
    disabled=_fetch_status == "running",
    key="top_fetch_selected",
):
    # The primary flow is a rolling newest-first crawl: first refresh the latest
    # window, then continue with the next not-yet-loaded market pages.
    st.session_state["continue_market_after_latest"] = True
    start_fetch(fetch_category, True, "latest")
    st.rerun()
st.caption(
    "En knapp gör båda delarna: först hämtas nya annonser som kommit sedan sist, "
    "därefter fortsätter FlipFynd automatiskt med äldre annonser som ännu inte lästs in."
)
if _fetch_status == "running":
    st.info(fetch_progress_message() or "Hämtningen pågår… Annonser sparas sida för sida.")
    if st.button("⏹ Avbryt hämtning", key="top_stop_fetch"):
        stop_fetch()
        st.rerun()
elif _fetch_status == "finished" and st.session_state.pop("continue_market_after_latest", False):
    # Chain the archive-growth pass only after a successful latest refresh.
    # market_batch uses persisted coverage state and therefore starts at the
    # next not-yet-loaded page instead of rescanning the newest window.
    if start_fetch(fetch_category, True, "market_batch"):
        st.session_state["fetch_last_message"] = (
            "De senaste annonserna är kontrollerade. Fortsätter automatiskt "
            "med nästa ännu inte inlästa annonser…"
        )
        st.rerun()
elif _fetch_status == "failed":
    st.error(st.session_state.get("fetch_last_message") or "Hämtningen misslyckades. Försök igen.")
    log_tail = read_fetch_log_tail()
    if log_tail:
        with st.expander("Tekniska detaljer"):
            st.code(log_tail, language="text")

# Advanced fetch controls are intentionally hidden from the normal flow.
# The primary button above both refreshes newest listings and extends the archive.
with st.expander("Avancerade hämtningsinställningar", expanded=False):
    extra_modes = {
        "Uppdatera äldre sparade sidor": "scheduled_refresh",
        "Full genomsökning (tar längre tid)": "full",
    }
    extra_mode = st.selectbox("Omfattning", list(extra_modes), key="extra_fetch_mode")
    if st.button(
        "Kör avancerad hämtning",
        disabled=_fetch_status == "running",
        key="extra_fetch_start",
    ):
        start_fetch(fetch_category, True, extra_modes[extra_mode])
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
        ("Fysiska kortannonser", int(debug.get("integrity_eligible_candidates", debug.get("after_feature_filters", 0)) or 0)),
        ("Snabbanalyserade", int(debug.get("fast_pool_selected", debug.get("final_results", 0)) or 0)),
        ("Djupanalyserade", int(debug.get("deep_analysed_candidates", debug.get("full_analysis", 0)) or 0)),
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


# Pedagogiskt huvudflöde. Hitta fynd låses under aktiv hämtning så användaren
# aldrig behöver fundera på om analysen körs mot ett halvfärdigt dataset.
_flow_fetching = st.session_state.get("fetch_status") == "running"
if not _has_data:
    _flow_step = "1"
    _flow_title = "HÄMTA ANNONSER"
    _flow_text = "Det finns ännu inga annonser att analysera. Välj Hockey, Fotboll eller Båda ovan och hämta data först."
elif _flow_fetching:
    _flow_step = "2"
    _flow_title = "VÄNTA TILLS HÄMTNINGEN ÄR KLAR"
    _flow_text = "FlipFynd sparar annonser löpande, men Hitta fynd är låst tills pågående hämtning är färdig. Då analyseras ett stabilt dataset."
else:
    _flow_step = "3"
    _flow_title = "HITTA FYND"
    _flow_text = "Data är redo. Välj sport och budget. Börja med tom sökruta och utan avancerade filter, tryck sedan Hitta fynd."

st.markdown(
    f"""
    <div class="ff-data-card">
      <h3>🧭 SÅ FUNKAR FLÖDET</h3>
      <p><b>1. Hämta</b> → FlipFynd läser in annonser.</p>
      <p><b>2. Välj budget</b> → du behöver normalt inte röra avancerade filter.</p>
      <p><b>3. Köp eller avstå</b> → börja med Bästa köpet just nu. Öppna detaljer bara när du vill förstå varför.</p>
      <p><b>Just nu – steg {_flow_step}: {_flow_title}</b><br>{_flow_text}</p>
    </div>
    """,
    unsafe_allow_html=True,
)
if _flow_fetching:
    st.info("⏳ Hämtning pågår. Hitta fynd låses automatiskt upp när hämtningen är klar.")
elif _has_data:
    st.success("✅ Annonsdata är redo. Du kan trycka Hitta fynd nu.")
else:
    st.warning("📥 Börja med att hämta annonser ovan. Hitta fynd blir aktiv när data finns och ingen hämtning pågår.")


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

    # En enda standardmotor: användaren ska inte behöva välja analysstrategi.
    # premium_flip är den bredaste fyndmotorn och kombineras längre ned med
    # efterfrågan, risk, samlarmerit, comps och verifierad ekonomisk edge.
    strategy = "premium_flip"

    search = st.text_input(
        "Sök spelare, set eller kort",
        value="",
        placeholder="T.ex. Bedard, Young Guns, Messi…",
        help="Lämna tomt för att låta FlipFynd hitta de bästa fynden i hela den valda sporten.",
    )
    effective_search = normalize_sport_category_search(search, sport)
    st.caption(
        "Sökningen fokuserar på senaste snabba hämtningen. "
        "Under Avancerade filter kan du även ta med äldre sparade annonser."
    )
    if str(search or "").strip() and not str(effective_search or "").strip():
        st.caption(
            f"{sport_label} är redan valt ovan. FlipFynd söker därför i alla {sport_label.lower()}kort "
            "i stället för att bara matcha annonser som råkar innehålla kategorinamnet."
        )

    with st.expander("Avancerade filter"):
        include_older = st.checkbox(
            "Ta med äldre sparade annonser",
            value=False,
            help="Normalt analyseras senaste snabba hämtningen per sport. Äldre data används om en sådan hämtning saknas.",
        )
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
                value=False,
                help="Slå på endast om du vill se kort som inte är tillräckligt starka för huvudlistan.",
            )

        st.caption(
            "Autografer, numrerade kort och patch/relic ingår alltid i den vanliga fyndsökningen. "
            "Filtren nedan används bara om du vill begränsa sökningen till en viss korttyp."
        )
        card_type_filter = st.radio(
            "Korttyp",
            ["Alla kort", "Endast autograf", "Endast numrerade", "Endast patch/relic"],
            horizontal=True,
            key="ordinary_card_type_filter",
        )
        auto_only = card_type_filter == "Endast autograf"
        numbered_only = card_type_filter == "Endast numrerade"
        patch_only = card_type_filter == "Endast patch/relic"

    # Intern prestandaparameter: användaren ska inte behöva förstå den.
    # Keep the interactive Streamlit request bounded. The background worker
    # can use a wider deep pass once deployed.
    full_limit = 8

    _find_disabled = (not _has_data) or _flow_fetching
    if _flow_fetching:
        _find_label = "⏳ Vänta – annonser hämtas"
    elif not _has_data:
        _find_label = "📥 Hämta annonser först"
    else:
        _find_label = "🔎 Hitta fynd"
    run = st.form_submit_button(
        _find_label,
        type="primary",
        use_container_width=True,
        disabled=_find_disabled,
        help=(
            "Knappen låses medan en hämtning pågår. Vänta tills hämtningen visar KLAR."
            if _flow_fetching
            else "Analyserar redan inlästa annonser – den hämtar inte ny data."
        ),
    )

    clear_main_search = st.form_submit_button(
        "🧹 Rensa huvudsökning",
        use_container_width=True,
        help="Rensar visade resultat och sessionscache. Nästa Hitta fynd körs med aktuell appversion.",
    )


if clear_main_search:
    st.session_state["results"] = None
    st.session_state["debug"] = None
    st.session_state["result_cache"] = {}
    st.session_state.pop("active_search_job_id", None)
    st.session_state.pop("results_data_version", None)
    # "Rensa huvudsökning" means a genuinely fresh market search, not merely
    # hiding the old result cards. Remove the loaded listing snapshot as well.
    try:
        clear_all_loaded_data()
    except Exception:
        pass
    try:
        get_data.clear()
    except Exception:
        pass
    st.session_state["fetch_status"] = "idle"
    st.session_state["fetch_last_message"] = ""
    st.success("Huvudsökningen och inlästa annonser är rensade. Hämta nya annonser innan nästa Hitta fynd.")
    st.rerun()


if run:
    status = st.status("🔎 FlipFynd startar analysen…", expanded=True)
    status.write(f"1/3 • Förbereder {sport_label.lower()}annonser inom din budget på {int(max_price)} kr.")
    progress = st.progress(12, text="Förbereder annonser…")
    status.write("2/3 • Analyserar kort, efterfrågan, risk, comps och möjlig vinst. Det kan ta en stund om många annonser ska bedömas.")
    progress.progress(35, text="Analyserar och rankar fynd…")
    try:
        # A running Streamlit process may retain the pre-v0.14.34 helper.
        # Encode scope in an existing argument, so both signatures work and
        # latest-only results can never be reused for an archive search.
        ANALYSIS_ENGINE_VERSION = "ordinary-v2-no-negative-padding-20260919-3"
        scoped_data_version = json.dumps(
            [get_data_version(), "archive" if include_older else "latest", ANALYSIS_ENGINE_VERSION],
            separators=(",", ":"),
        )
        current_run_signature = build_search_run_signature(
            data_version=scoped_data_version, app_version=APP_VERSION, sport=sport,
            search=effective_search, max_price=max_price, sale_type=sale_type,
            strategy=strategy, numbered_only=numbered_only, patch_only=patch_only,
            auto_only=auto_only,
        )
        # Prefer the in-session cache, then recover the same completed search
        # from durable Postgres storage after navigation/reconnect.
        reusable = get_reusable_search(st.session_state.get("result_cache"), current_run_signature)
        # Recover a completed background job for this exact search before
        # falling back to synchronous analysis.
        if not reusable and jobs_available():
            try:
                completed_job = latest_completed_job(
                    job_kind="ordinary_search", signature=current_run_signature
                )
                completed = unpack_completed_ordinary_job(completed_job)
                if completed:
                    results, debug = completed
                    reusable = (results, debug)
            except Exception:
                pass
        database_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
        if not reusable and database_url:
            try:
                durable_cache = load_persistent_namespace(
                    database_url, "ordinary_search:" + current_run_signature, {}
                )
                reusable = get_reusable_search(durable_cache, current_run_signature)
                if reusable:
                    st.session_state["result_cache"] = durable_cache
            except Exception:
                reusable = None
        if reusable:
            results, debug = reusable
            debug = dict(debug)
            debug["reused_completed_search"] = True
            progress.progress(90, text="Återanvänder färdig analys…")
            status.write("2/3 • Samma annonser och filter är redan analyserade. Återanvänder det färdiga resultatet.")
        else:
            # Queue the expensive analysis when durable jobs are available.
            # A separate worker can then continue after browser disconnect.
            active_job = None
            if jobs_available():
                try:
                    active_job = latest_active_job(
                        job_kind="ordinary_search", signature=current_run_signature
                    )
                    if not active_job:
                        payload = build_ordinary_search_job_payload(
                            sport=sport, search=effective_search, max_price=max_price,
                            sale_type=sale_type, full_limit=full_limit, strategy=strategy,
                            numbered_only=numbered_only, patch_only=patch_only,
                            auto_only=auto_only, include_older=include_older,
                            data_version=scoped_data_version, app_version=APP_VERSION,
                        )
                        active_job = create_job(
                            job_kind="ordinary_search", payload=payload,
                            signature=current_run_signature,
                        )
                except Exception:
                    active_job = None
            if active_job:
                # Until a separate worker is deployed, QUEUED jobs would make
                # the user wait forever and show no result. Only hand off when
                # a worker has actually claimed the job.
                if str(active_job.get("status") or "") == "RUNNING":
                    st.session_state["active_search_job_id"] = active_job["job_id"]
                    status.update(label="⏳ Analysen fortsätter i bakgrunden", state="running", expanded=False)
                    progress.progress(int(active_job.get("progress") or 1), text="Bakgrundsanalys pågår – du kan lämna appen.")
                    st.info("Bakgrundsanalysen är aktiv. Du kan byta app och komma tillbaka senare.")
                    st.stop()
                # No worker has claimed it: run synchronously now so Hitta fynd
                # always produces a result instead of silently parking in QUEUED.
                active_job = None
            results, debug = analyze_data(
                data=data, sport=sport, search=effective_search,
                max_price=max_price, sale_type=sale_type, full_limit=full_limit,
                strategy=strategy, numbered_only=numbered_only,
                patch_only=patch_only, auto_only=auto_only,
                include_older=include_older,
            )
            debug["reused_completed_search"] = False
            st.session_state["result_cache"] = store_reusable_search(current_run_signature, results, debug)
            if database_url:
                try:
                    save_persistent_namespace(
                        database_url,
                        "ordinary_search:" + current_run_signature,
                        st.session_state["result_cache"],
                    )
                except Exception:
                    pass
        progress.progress(90, text="Sorterar de bästa kandidaterna…")
        elapsed_text = "direkt från cache" if debug.get("reused_completed_search") else f"{debug.get('total_analysis_seconds', 0):.1f} s"
        status.write(f"3/3 • Klart på {elapsed_text}. {int((debug or {}).get('final_results', len(results)) or 0)} annonser nådde analyssteget.")
        progress.progress(100, text="Klar")
        status.update(label="✅ Analysen är klar – resultaten visas nedan", state="complete", expanded=False)
    except Exception as exc:
        status.update(label="❌ Analysen kunde inte slutföras", state="error", expanded=True)
        st.error("Något gick fel under fyndanalysen. Dina inställningar är sparade; försök igen eller öppna tekniska detaljer i Administration & data.")
        raise

    # Persist immediately after successful analysis so a later Streamlit
    # rerun/navigation cannot make the user press Hitta fynd twice.
    st.session_state["results"] = results
    st.session_state["debug"] = debug
    st.session_state["results_data_version"] = get_data_version()
    st.session_state["last_completed_search_signature"] = current_run_signature
    if database_url:
        try:
            save_persistent_namespace(
                database_url,
                "ordinary_last_completed",
                {"signature": current_run_signature, "results": results, "debug": debug},
            )
        except Exception:
            pass


def render_same_seller_button(item: dict, key: str) -> None:
    """Find more cards from the same seller so shipping may be shared."""
    seller_market = list(data or [])
    seller, item = recover_seller_from_market(item, seller_market)
    label = "🧺 Fler kort från samma säljare"
    with st.popover(label, use_container_width=True):
        if not seller:
            st.info("FlipFynd hittar ännu inget säkert säljaralias för just den här annonsen. Annonsen har först matchats mot den inlästa marknaden.")
            return
        st.markdown(f"### 🧺 Samfraktsjakt hos {seller}")
        st.caption("FlipFynd börjar med den inlästa marknaden. Med Tradera API kan du dessutom hämta säljarens hela aktiva lager direkt.")

        creds = _resolve_tradera_api_credentials()
        api_key = f"seller_inventory_api_{key}_{seller}"
        if creds:
            if st.button("🌐 Hämta alla aktiva annonser från säljaren", key=api_key, use_container_width=True):
                with st.spinner(f"Hämtar aktiva annonser från {seller} via Tradera…"):
                    fetched = discover_active_seller_inventory(
                        seller_alias=seller,
                        app_id=creds[0],
                        app_key=creds[1],
                        category_id=0,
                    )
                st.session_state[f"seller_inventory_result_{key}"] = fetched
            fetched = st.session_state.get(f"seller_inventory_result_{key}") or {}
            if fetched.get("ok"):
                api_items = fetched.get("items") or []
                seller_market.extend(api_items)
                st.success(f"Tradera API hittade {len(api_items)} aktiva annonser hos {seller}.")
                st.caption("API-listan är discovery-data. Varje kort måste fortfarande analyseras och verifieras innan det kan bli en add-on-rekommendation.")

                quick_key = f"seller_inventory_quick_{key}_{seller}"
                if st.button("⚡ Snabbanalysera säljarens livekort", key=quick_key, use_container_width=True):
                    anchor_sport = infer_item_sport(item) or "hockey"
                    with st.spinner("Snabbanalyserar säljarens mest lovande kort…"):
                        quick = quick_analyze_seller_inventory(
                            item,
                            api_items,
                            analyze_fn=analyze_item,
                            sport=anchor_sport,
                            strategy_mode="quick_flip",
                            limit=20,
                            shortlist=5,
                        )
                    st.session_state[f"seller_inventory_quick_result_{key}"] = quick

                quick = st.session_state.get(f"seller_inventory_quick_result_{key}") or {}
                if quick.get("rows"):
                    # Feed fast-analysis results back into the same-seller list so
                    # existing add-on labels can use the newly discovered evidence.
                    seller_market.extend([r.get("source_item") for r in quick.get("rows", []) if r.get("source_item")])
                    st.markdown("#### ⚡ 2–5 kort att titta vidare på")
                    st.caption("Det här är en research-shortlist, inte en köporder. Full analys krävs innan ett kort kan rekommenderas.")
                    for qidx, qrow in enumerate(quick.get("shortlist") or [], start=1):
                        qprice = qrow.get("price")
                        price_text = f" · {qprice:.0f} kr" if isinstance(qprice, (int, float)) else ""
                        st.markdown(f"**{qidx}. {qrow.get('title')}**{price_text}")
                        st.caption(
                            f"{qrow.get('label')} · researchscore {qrow.get('quick_score', 0):.0f}/100 · "
                            f"identitet {qrow.get('identity_score', 0):.0f}/100 · {qrow.get('sold_comps', 0)} SOLD"
                        )
                        st.caption(qrow.get("reason"))
                        action_cols = st.columns(2)
                        with action_cols[0]:
                            full_key = f"seller_quick_full_{key}_{qidx}"
                            if st.button("🔬 Fullanalysera", key=full_key, use_container_width=True):
                                anchor_sport = infer_item_sport(item) or "hockey"
                                with st.spinner("Kör full FlipFynd-analys av kortet…"):
                                    try:
                                        full_result = full_analyze_live_seller_item(
                                            qrow.get("source_item") or {},
                                            analyze_fn=analyze_item,
                                            all_items=seller_market,
                                            sport=anchor_sport,
                                            strategy_mode="quick_flip",
                                        )
                                    except Exception as exc:
                                        full_result = {"ok": False, "error": str(exc)}
                                st.session_state[f"seller_live_full_{key}_{qidx}"] = full_result
                        with action_cols[1]:
                            if qrow.get("url"):
                                st.link_button("Öppna annons ↗", qrow["url"], key=f"seller_quick_link_{key}_{qidx}", use_container_width=True)

                        full_result = st.session_state.get(f"seller_live_full_{key}_{qidx}") or {}
                        if full_result:
                            if not full_result.get("ok"):
                                st.warning("Fullanalysen kunde inte slutföras för den här annonsen just nu.")
                            else:
                                st.markdown(f"**{full_result.get('label')} · {full_result.get('decision')}**")
                                st.caption(full_result.get("reason"))
                                facts = [
                                    f"identitet {full_result.get('identity_score', 0):.0f}/100",
                                    f"{full_result.get('sold_comps', 0)} SOLD",
                                    f"värderingssäkerhet {full_result.get('valuation_confidence', 0):.0f}/100",
                                ]
                                total_cost = full_result.get("total_cost")
                                max_buy = full_result.get("max_price")
                                if isinstance(total_cost, (int, float)):
                                    facts.append(f"kostnad {total_cost:.0f} kr")
                                if isinstance(max_buy, (int, float)):
                                    facts.append(f"maxpris {max_buy:.0f} kr")
                                st.caption(" · ".join(facts))
                                if full_result.get("source_item"):
                                    seller_market.append(full_result["source_item"])
                    if quick.get("failed_count"):
                        st.caption(f"{quick['failed_count']} liveannons kunde inte snabbanalyseras och ignorerades.")
            elif fetched:
                st.warning("Tradera kunde inte hämta säljarens aktiva lager just nu. FlipFynd använder den redan inlästa marknaden som fallback.")
        else:
            st.caption("Tradera API-nycklar saknas, så samfraktsjakten använder den lokalt inlästa marknaden.")

        bundle = find_same_seller_listings(
            item,
            seller_market,
            results=st.session_state.get("results") or [],
            limit=30,
        )
        if not bundle.get("rows"):
            st.info("Inga andra aktiva annonser från samma säljare hittades i tillgänglig marknadsdata.")
            return
        st.success(f"Hittade {bundle['count']} andra kortannonser från samma säljare.")
        st.markdown("#### 🎯 Bygg bästa paketet automatiskt")
        anchor_price = float(item.get("pris") or item.get("price") or 0)
        default_budget = max(500, int(anchor_price + 250))
        basket_budget = st.number_input(
            "Maxbudget inklusive huvudkort och ett samfraktsscenario",
            min_value=50,
            max_value=100000,
            value=int(default_budget),
            step=50,
            key=f"seller_basket_budget_{key}",
        )
        best_basket = build_best_same_seller_basket(item, bundle["rows"], basket_budget)
        if best_basket.get("status") == "FOUND":
            names = [r.get("title") or "Kort" for r in best_basket.get("selected", [])]
            st.success(
                f"Bästa verifierbara paketet under {basket_budget:.0f} kr: "
                f"huvudkortet + {best_basket['selected_count']} extra kort · "
                f"scenario {best_basket['scenario_total']:.0f} kr · "
                f"{best_basket['remaining_budget']:.0f} kr kvar."
            )
            for name in names:
                st.write(f"• {name}")
            scenario = best_basket.get("scenario") or {}
            if scenario.get("potential_shipping_saving"):
                st.caption(f"Teoretisk fraktbesparing: {scenario['potential_shipping_saving']:.0f} kr.")
            st.caption(best_basket.get("note"))
        elif best_basket.get("status") == "NO_ELIGIBLE_ADDONS":
            st.info("Inga extra kort är ännu tillräckligt starka och verifierade för att FlipFynd automatiskt ska lägga dem i paketet.")
        elif best_basket.get("status") == "NO_FIT":
            st.info("Det finns starka add-on-kandidater, men ingen ryms inom den valda totalbudgeten.")
        elif best_basket.get("status") == "ANCHOR_OVER_BUDGET":
            st.warning("Huvudkortet plus dess angivna frakt ligger redan över vald budget.")
        else:
            st.caption("Automatisk paketoptimering kräver känt pris och känd frakt på huvudkortet.")
        if best_basket.get("excluded_unknown_shipping"):
            st.caption(f"{best_basket['excluded_unknown_shipping']} stark kandidat med okänd frakt hölls utanför auto-korgen för att budgeten inte ska bli missvisande.")
        st.divider()
        selected = []
        for idx, row in enumerate(bundle["rows"], start=1):
            with st.container(border=True):
                cols=st.columns([5,1])
                cols[0].markdown(f"**{idx}. {row['title']}**")
                cols[1].markdown(f"**{row['price']:.0f} kr**")
                bits=[]
                if row.get("shipping") is not None:
                    bits.append(f"ordinarie frakt {row['shipping']:.0f} kr")
                if row.get("analysed"):
                    bits.append(f"analyserad · {row.get('decision') or 'ej köpbeslut'}")
                    if row.get("potential") is not None:
                        bits.append(f"fyndpotential {row['potential']:.0f}/100")
                    bits.append(f"{row.get('sold_comps',0)} SOLD")
                else:
                    bits.append("inte fullanalyserad ännu")
                st.caption(" · ".join(bits))
                addon = classify_same_seller_addon(row)
                if addon.get("status") == "ADD":
                    st.success(f"✅ {addon['label']} — {addon['reason']}")
                elif addon.get("status") == "REVIEW":
                    st.info(f"🟡 {addon['label']} — {addon['reason']}")
                else:
                    st.caption(f"⚪ {addon['label']} — {addon['reason']}")
                if st.checkbox("Ta med i samfraktsscenario", key=f"seller_bundle_{key}_{idx}"):
                    selected.append(row)
                if row.get("url"):
                    st.link_button("Öppna den här annonsen ↗", row["url"], use_container_width=True)
        if selected:
            scenario=build_shared_shipping_scenario(item, selected)
            st.markdown("#### Frakt-som-betalas-en-gång-scenario")
            c1,c2,c3=st.columns(3)
            c1.metric("Kortens pris", f"{scenario.get('item_total',0):.0f} kr")
            c2.metric("Frakt en gång", f"{scenario['shipping_once']:.0f} kr" if scenario.get("shipping_once") is not None else "Ej känt")
            c3.metric("Scenario totalt", f"{scenario['scenario_total']:.0f} kr" if scenario.get("scenario_total") is not None else "Ej känt")
            if scenario.get("potential_shipping_saving") is not None and scenario.get("potential_shipping_saving") > 0:
                st.success(f"Teoretisk fraktbesparing: {scenario['potential_shipping_saving']:.0f} kr jämfört med att betala de angivna frakterna separat.")
            st.warning(scenario.get("note"))
            st.caption("FlipFynd ändrar inte kortens marknadsvärde bara för att frakten kan delas. Varje extrakort måste fortfarande vara ett rimligt köp i sig.")


def render_card_explanation_button(item: dict, key: str) -> None:
    """Render a one-click, evidence-aware explanation for a listing card."""
    explanation = build_card_explanation(item)
    identity = build_card_identity_summary(item)
    with st.popover("✨ Varför är just det här kortet intressant?", use_container_width=True):
        st.markdown("### 🪪 Vad är det här för kort?")
        for row in identity.get("rows", []):
            level = row.get("level")
            icon = "✅" if level == "verified" else "🔎" if row.get("known") else "◻️"
            source = f" · _{row.get('source')}_" if row.get("source") else ""
            st.write(f"{icon} **{row.get('label')}:** {row.get('value')}{source}")
        st.caption(f"Identitetsstatus: {identity.get('status_text')}")
        if identity.get("missing"):
            st.caption("Saknas fortfarande för verifierad exact identity: " + ", ".join(identity["missing"]))
        if identity.get("supports_exact_comp_search"):
            st.success("Identiteten är tillräckligt komplett för exact-comp-sökning.")
        else:
            st.warning("Exakt kortidentitet är inte tillräckligt säker ännu. Värderingen ska därför tolkas försiktigt.")
        st.divider()
        st.markdown(f"**{explanation['headline']}**")
        if explanation.get("strengths"):
            st.markdown("**Det som talar för kortet**")
            for reason in explanation["strengths"]:
                st.write("✅ " + str(reason))
        if explanation.get("comparison"):
            st.markdown("**Varför samlare kan bry sig om just den här versionen**")
            for point in explanation["comparison"]:
                st.write("↔️ " + str(point))
        if explanation.get("evidence"):
            st.markdown("**Vad FlipFynd faktiskt har stöd för**")
            for fact in explanation["evidence"]:
                st.write("• " + str(fact))
        if explanation.get("rarity_context"):
            st.markdown("**Checklist / case hit / short print**")
            for fact in explanation["rarity_context"]:
                st.write("🎯 " + str(fact))
        if explanation.get("stronger_if"):
            st.markdown("**Vad som skulle göra caset starkare**")
            for point in explanation["stronger_if"]:
                st.write("🔎 " + str(point))
        if explanation.get("cautions"):
            st.markdown("**Det du inte ska övertolka**")
            for caution in explanation["cautions"]:
                st.write("⚠️ " + str(caution))
        st.caption("Observerade uppgifter från annonstiteln visas separat från verifierad exact identity. FlipFynd hittar inte på rookieår, raritet eller marknadsvärde.")


if st.session_state.get("results") is not None:
    filtered = []

    for item in st.session_state["results"]:
        if item.get("confidence", 0) < minimum_confidence:
            continue

        if not show_skip and item.get("beslut") == "SKIP":
            continue

        filtered.append(item)

    visible = filtered[: int(show_count)]

    # Novice navigation layer: reorganises existing analysis without creating new decisions.
    if not _advanced_terminal:
        st.divider()
        if _main_view == "Vad ska jag köpa?":
            simple_buy = build_buy_view(filtered)
            st.subheader("🎯 Ditt beslut just nu")
            st.caption("Ett tydligt förstaval – eller ett tydligt besked att avstå.")
            if simple_buy.get("status") == "READY" and simple_buy.get("card"):
                card = simple_buy["card"]
                st.success(f"### KÖP · {card['title']}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Kostar nu", f"{card['total_cost']:.0f} kr" if card.get("total_cost") is not None else "Ej säkert")
                shipping_label = card.get("shipping_label") or ("Frakt" if card.get("shipping_known") else "Antagen frakt")
                c2.metric(shipping_label, f"{card['shipping']:.0f} kr" if card.get("shipping") is not None else "Ej säkert")
                c3.metric("Uppskattat marknadsvärde", f"{card['expected_resale']:.0f} kr" if card.get("expected_resale") is not None else "Otillräckligt underlag")
                c4, c5 = st.columns(2)
                c4.metric("Betala högst", f"{card['max_total_price']:.0f} kr" if card.get("max_total_price") is not None else "Ej säkert")
                c5.metric("Möjlig nettovinst", f"{card['net_profit']:+.0f} kr" if card.get("net_profit") is not None else "Ej säkert")
                reasons=[]
                if card.get("expected_days") is not None:
                    reasons.append(f"verifierad säljtid ~{card['expected_days']:.0f} dagar")
                reasons.append(identity_text(card.get("exact_identity_status")))
                reasons.append(sold_evidence_text(card.get("sold_comparable_count")))
                reasons.append(sellability_text(card.get("sellability_label"), card.get("sellability_score")))
                st.caption(" · ".join(reasons))
                render_card_explanation_button(card, "simple_buy")
                render_same_seller_button(card, "simple_buy")
                if card.get("url"):
                    st.link_button("Öppna annonsen på Tradera ↗", card["url"], use_container_width=True)
                with st.expander("Varför väljer FlipFynd detta kort?", expanded=False):
                    for reason in card.get("reasons") or []:
                        st.write("• " + str(reason))
                    st.caption(simple_buy.get("note") or "")
            else:
                st.info("Inget SOLD-verifierat förstaval just nu. Möjliga fynd från begärda priser visas separat nedan.")
                st.caption(simple_buy.get("note") or "")

            render_asking_price_shortlist(st.session_state.get("results") or [])

            # One compact Top 5. Research signals may rank UNDERSÖK candidates,
            # but KÖP remains gated by verified economic evidence.
            decision_tiers = build_decision_tiers_compat(
                build_decision_tiers,
                st.session_state.get("results") or [],
                total_limit=5,
                require_verified_economic_edge=True,
            )
            opportunity_top5 = build_opportunity_top5(st.session_state.get("results") or [], limit=5)
            top_rows = list(opportunity_top5.get("rows") or [])

            st.markdown("### 🏆 Topp 5 i den här sökningen")
            if not top_rows:
                st.warning(
                    "Inga kandidater med positiv eller ännu okänd fyndmarginal hittades i den analyserade gruppen. "
                    "FlipFynd visar inte längre kända minusaffärer bara för att fylla Top 5."
                )
            else:
                tier_labels = {
                    "VERIFIED": "Verifierat fynd",
                    "PROMISING": "Lovande · undersök",
                    "REMAINDER": "Bäst av resten",
                }
                table_rows = []
                for rank, row in enumerate(top_rows, start=1):
                    total = row.get("total_cost")
                    market = row.get("market_value")
                    net = row.get("estimated_net_profit")
                    asking = row.get("asking_reference")
                    heuristic = row.get("heuristic_indication")
                    price_indication = market if market is not None else (asking if asking is not None else heuristic)
                    indication_source = (
                        "SOLD/verifierat" if market is not None
                        else ("Aktuella priser" if asking is not None
                              else ("Modell/guide" if heuristic is not None else "Saknas"))
                    )
                    table_rows.append({
                        "#": rank,
                        "Kort": row.get("title") or "Okänt kort",
                        "Status": "KÖP" if row.get("decision") == "KÖP" else "UNDERSÖK",
                        "Kostnad": f"{float(total):.0f} kr" if total is not None else "–",
                        "Prisindikation": f"{float(price_indication):.0f} kr" if price_indication is not None else "–",
                        "Underlag": indication_source,
                        "Möjlig marginal": (
                            f"{float(price_indication-total):+.0f} kr"
                            if price_indication is not None and total is not None else "–"
                        ),
                        "Fyndpotential": f"{float(row.get('potential') or 0):.0f}/100",
                        "Säkerhet": f"{float(row.get('certainty') or 0):.0f}/100",
                    })
                st.dataframe(table_rows, use_container_width=True, hide_index=True)
                negative_count = sum(1 for row in top_rows if row.get("best_of_bad_market"))
                if negative_count:
                    st.warning(
                        f"{negative_count} av fem kandidater har redan negativ prisindikation och visas bara eftersom "
                        "det saknas bättre prisbedömda alternativ. De är inte fynd – kontrollera kandidater utan prisdata först."
                    )
                st.caption("Prisindikation används för fyndjakt. SOLD ger starkare bekräftelse när det finns, men krävs inte för UNDERSÖK.")
                for rank, row in enumerate(top_rows, start=1):
                    with st.expander(f"#{rank} · {row.get('title') or 'Okänt kort'}", expanded=False):
                        st.write(f"**{row.get('decision') or 'UNDERSÖK'}** · {tier_labels.get(row.get('tier'), 'Bäst av resten')}")
                        facts = []
                        if row.get("total_cost") is not None:
                            facts.append(f"total kostnad {float(row['total_cost']):.0f} kr")
                        if row.get("market_value") is not None:
                            facts.append(f"prisindikation {float(row['market_value']):.0f} kr (verifierat underlag)")
                        elif row.get("asking_reference") is not None:
                            facts.append(f"prisindikation {float(row['asking_reference']):.0f} kr (aktuella begärda priser)")
                        elif row.get("heuristic_indication") is not None:
                            facts.append(f"prisindikation {float(row['heuristic_indication']):.0f} kr (modell/guide – kontrollera själv)")
                        else:
                            facts.append("prisindikation saknas")
                        facts.append(f"{int(row.get('sold_comps') or 0)} verifierade SOLD")
                        st.caption(" · ".join(facts))
                        if row.get("reasons"):
                            st.caption("Varför: " + " · ".join(row.get("reasons") or []))
                        if row.get("primary_blocker"):
                            st.caption("Kontrollera först: " + str(row["primary_blocker"]))
                        render_card_explanation_button(row.get("_source_item") or row, f"top5_{rank}")
                        render_same_seller_button(row.get("_source_item") or row, f"top5_{rank}")
                        if row.get("url"):
                            st.link_button("Öppna annonsen ↗", row["url"], use_container_width=True)
                st.caption(opportunity_top5.get("note") or "")

            with st.expander("🔬 Avancerad fyndjakt / så tänker FlipFynd", expanded=False):
                coverage = evidence_coverage(st.session_state.get("results") or [])
                if coverage.get("total"):
                    st.caption(
                        f"Evidens: {coverage['with_2_sold']}/{coverage['total']} har minst 2 exact SOLD · "
                        f"{coverage.get('research_identity_ready',0)}/{coverage['total']} har sökbar comp-identitet · "
                        f"{coverage['market_value_ready']}/{coverage['total']} har säkert marknadsvärde."
                    )
                if decision_tiers.get("rejection_reasons"):
                    common = sorted(decision_tiers["rejection_reasons"].items(), key=lambda kv: kv[1], reverse=True)[:3]
                    st.caption("Vanligaste verifieringsluckorna: " + " · ".join(f"{reason} ({count})" for reason, count in common))

                segment_yield = build_segment_yield_report(
                    st.session_state.get("results") or [],
                    budget=max_price,
                    minimum_hits=8,
                )
                if segment_yield.get("rows"):
                    with st.expander("📊 Vilka delar av marknaden ger bäst fyndunderlag?", expanded=False):
                        st.caption(
                            "Detta är observerad yield från den aktuella analysen. "
                            "FlipFynd ändrar inte KÖP-regler eller analysbudget automatiskt."
                        )
                        strongest = best_observed_segments(segment_yield, limit=3)
                        if strongest:
                            for srow in strongest:
                                st.write(f"**{srow['segment']}**")
                                st.caption(
                                    f"{srow['hits']} analyserade · {srow['verified']} verifierade fynd · "
                                    f"{srow['promising']} lovande · {srow['safe_value']} med säkert värde · "
                                    f"{srow['evidence_status']}"
                                )
                        else:
                            st.info(
                                f"Inget segment har ännu minst {segment_yield.get('minimum_hits', 8)} analyserade kort. "
                                "FlipFynd samlar mer underlag innan segment jämförs."
                            )
                        st.caption(segment_yield.get("note") or "")

        elif _main_view == "Slutar snart":
            ending_view = build_ending_soon_view(filtered)
            st.subheader("⏳ Slutar snart")
            st.caption("Auktioner som slutar snart och där FlipFynd redan har tillräckligt underlag för att sätta ett säkert maxpris.")
            if ending_view["status"] == "EMPTY":
                st.info("Inga verifierade auktioner som både slutar snart och klarar FlipFynds säkerhetskrav just nu.")
            for row in ending_view["rows"]:
                with st.container(border=True):
                    mins=row.get("remaining_minutes")
                    when=f"ca {mins} min kvar" if mins is not None else "sluttid ej säker"
                    st.markdown(f"**{row['title']}**")
                    st.write(f"{when} · nuvarande beslut: **{row.get('decision') or 'Ej bedömt'}**")
                    market_value_text = f"{float(row['market_value']):.0f} kr" if row.get("market_value") is not None else "Otillräckligt underlag"
                    st.write(f"Uppskattat marknadsvärde: **{market_value_text}**")
                    if row.get("total_cost") is not None and row.get("max_total_price") is not None:
                        shipping_part = f"frakt {float(row['shipping']):.0f} kr" if row.get("shipping_known") else f"antagen frakt {float(row.get('shipping') or 29):.0f} kr"
                        st.caption(f"Kostar nu {float(row['total_cost']):.0f} kr · {shipping_part} · betala högst {float(row['max_total_price']):.0f} kr")
                    if row.get("url"):
                        st.link_button("Öppna auktionen ↗", row["url"], use_container_width=True)
            st.caption(ending_view["note"])

        elif _main_view == "Bevaka":
            watch_view = build_watch_view(filtered)
            st.subheader("👀 Bevaka")
            st.caption("Intressanta kort där något fortfarande saknas innan köp känns tillräckligt säkert.")
            if watch_view["status"] == "EMPTY":
                st.info("Inga tydliga bevakningskandidater i den aktuella analysen.")
            for row in watch_view["rows"]:
                with st.container(border=True):
                    st.markdown(f"**{row['title']}**")
                    st.write(f"Nuvarande beslut: **{row.get('decision') or 'BEVAKA'}**")
                    market_value_text = f"{float(row['market_value']):.0f} kr" if row.get("market_value") is not None else "Otillräckligt underlag"
                    st.write(f"Uppskattat marknadsvärde: **{market_value_text}**")
                    if row.get("primary_blocker"):
                        st.caption("Det som stoppar köp nu: " + str(row["primary_blocker"]))
                    elif row.get("sold_comps", 0) < 2:
                        st.caption("Det som stoppar köp nu: för få verifierade försäljningar att jämföra med.")
                    st.caption(identity_text(row.get("identity_status")) + " · " + sold_evidence_text(row.get("sold_comps")) + " · " + sellability_text(row.get("sellability_label"), row.get("sellability_score")))
                    if row.get("url"):
                        st.link_button("Öppna annonsen ↗", row["url"], use_container_width=True)
            st.caption(watch_view["note"])

        else:
            research_view = build_research_view(filtered)
            st.subheader("🔬 Research")
            st.caption("Saker som kan vara värda att kontrollera närmare. De är inte köpbeslut.")
            if research_view["status"] == "EMPTY":
                st.info("Inga tydliga researchsignaler i den aktuella analysen.")
            for row in research_view["rows"]:
                with st.container(border=True):
                    st.markdown(f"**{row['title']}**")
                    market_value_text = f"{float(row['market_value']):.0f} kr" if row.get("market_value") is not None else "Otillräckligt underlag"
                    st.write(f"Uppskattat marknadsvärde: **{market_value_text}**")
                    st.write(" · ".join(row.get("signals") or []))
                    if row.get("verify_first"):
                        st.caption("Verifiera först: " + ", ".join(row["verify_first"]))
                    st.caption(f"Ordinarie beslut är fortfarande: {row.get('decision') or 'Ej bedömt'}")
                    if row.get("url"):
                        st.link_button("Öppna annonsen ↗", row["url"], use_container_width=True)
            st.caption(research_view["note"])

        if _main_view == "Vad ska jag köpa?":
            funnel = build_finding_funnel_diagnostic(
                st.session_state.get("debug") or {},
                st.session_state.get("results") or [],
            )
            no_buy = funnel.get("decisions", {}).get("KÖP", 0) == 0
            expansion_category = "Hockey - NHL" if sport_label == "Hockey" else "Fotboll"
            expansion_plan = build_search_expansion_plan(
                st.session_state.get("results") or [],
                expansion_category,
                player_limit=6,
                max_searches=36,
            )
            if expansion_plan.get("searches"):
                with st.expander("🛰️ Search Expansion – fler sökvägar till fynd", expanded=False):
                    st.caption(
                        "FlipFynd bygger alternativa Tradera-sökningar från redan strukturerade spelarnamn och kortdata. "
                        "Sökningen skapar aldrig kortidentitet, marknadsvärde eller KÖP."
                    )
                    readiness = tradera_api_readiness()
                    creds = _resolve_tradera_api_credentials()
                    if creds:
                        st.success("Tradera API är konfigurerat för automatiserad sökning.")
                        if st.button("🔎 Kör Search Expansion nu", key=f"run_search_expansion_{expansion_category}"):
                            with st.spinner("Söker fler Tradera-annonser via säkra discovery-sökningar…"):
                                api_result = run_search_plan(
                                    expansion_plan,
                                    app_id=creds[0],
                                    app_key=creds[1],
                                    max_searches=12,
                                )
                                stored = save_expansion_items(
                                    SEARCH_EXPANSION_DATA_PATH,
                                    api_result.get("items") or [],
                                )
                                get_data.clear()
                                st.session_state["result_cache"] = {}
                                st.success(
                                    f"Search Expansion körde {api_result.get('searches_run', 0)} sökningar och "
                                    f"hittade {api_result.get('unique_items', 0)} unika API-träffar. "
                                    f"{stored} expansionsträffar finns nu i kandidatunderlaget."
                                )
                                st.rerun()
                    else:
                        st.info(
                            "Sökplanen är klar. Automatisk API-sökning aktiveras först när säkra Tradera API-uppgifter finns i miljön."
                        )
                    st.caption(
                        f"{len(expansion_plan.get('players_used') or [])} spelare · "
                        f"{int(expansion_plan.get('search_count', 0) or 0)} sökvägar"
                    )
                    for srow in (expansion_plan.get("searches") or [])[:12]:
                        st.write(f"**{srow['query']}** · {srow['order_by']}")
                        st.caption(f"{srow['kind']}: {srow['why']}")
                    if len(expansion_plan.get("searches") or []) > 12:
                        st.caption("Fler sökvägar finns i planen men döljs här för att hålla vyn enkel.")

            yield_report = build_yield_report(st.session_state.get("results") or [])
            if yield_report.get("rows"):
                with st.expander("📈 Search Yield – vilka sökvägar hittar bäst kandidater?", expanded=False):
                    st.caption("Observerad träffkvalitet, inte en ny fyndscore. KÖP-regler eller sökbudget ändras inte automatiskt.")
                    guidance = route_budget_guidance(yield_report, minimum_hits=10)
                    for yrow in guidance.get("rows", [])[:8]:
                        st.write(f"**{yrow['kind']} · {yrow['order_by']}**")
                        st.caption(f"{yrow['hits']} träffar · {yrow['buy']} KÖP · {yrow['watch']} BEVAKA · {yrow['safe_value']} säkra värden · {yrow['evidence_status']}")

            exact_supply_items = []
            for exact_item in st.session_state.get("results") or []:
                if not isinstance(exact_item, dict):
                    continue
                exact_plan = build_exact_supply_query(exact_item)
                if exact_plan.get("ready"):
                    exact_supply_items.append(exact_item)
                if len(exact_supply_items) >= 5:
                    break

            if exact_supply_items:
                with st.expander("🎯 Exact Card Supply – kontrollera just det här kortet", expanded=False):
                    st.caption(
                        "Här används bara kort som redan passerat Exact Identity Gate för comp-sökning. "
                        "Tradera-träffarna är kandidater tills de också passerat samma identitetskontroll."
                    )
                    exact_creds = _resolve_tradera_api_credentials()
                    for ei, exact_item in enumerate(exact_supply_items):
                        exact_plan = build_exact_supply_query(exact_item)
                        identity = exact_plan.get("identity_fields") or {}
                        player = identity.get("player_name") or "Okänd spelare"
                        set_name = identity.get("set_name") or ""
                        season = identity.get("season") or ""
                        card_number = identity.get("card_number") or ""
                        st.write(f"**{player} · {set_name} · {season} · #{card_number}**")
                        local_exact = count_analyzed_exact_matches(
                            exact_item,
                            st.session_state.get("results") or [],
                        )
                        st.caption(
                            f"{local_exact.get('exact_analyzed_matches', 0)} exakt identitetsmatchande aktiva kandidater "
                            "finns redan i FlipFynds analyserade pool."
                        )
                        st.caption(f"Säker sökfråga: `{exact_plan.get('query')}`")
                        confirmation_target = {**exact_item, "search_expansion_query": exact_plan.get("query")}
                        confirmation = build_confirmation_report(
                            confirmation_target,
                            st.session_state.get("results") or [],
                        )
                        if confirmation.get("rows"):
                            st.caption(
                                f"Efter identitetsanalys: {confirmation.get('confirmed_exact', 0)} bekräftade exakta · "
                                f"{confirmation.get('possible', 0)} möjliga · {confirmation.get('wrong_card', 0)} fel kort/konflikt."
                            )
                            for crow in confirmation.get("rows", [])[:6]:
                                st.write(f"• {crow['label']}: {crow.get('title') or 'Annons'}")

                        supply_history = load_history(EXACT_SUPPLY_HISTORY_PATH)
                        history_summary = summarize_history(confirmation_target, supply_history)
                        if history_summary.get("status") == "OK":
                            st.caption(
                                f"Historik: {history_summary.get('snapshots', 0)} observationer · "
                                f"{history_summary.get('direction')} · förändring "
                                f"{history_summary.get('change', 0):+d} bekräftade exakta."
                            )
                        elif history_summary.get("snapshots", 0):
                            st.caption(
                                f"Historik: {history_summary.get('snapshots', 0)} observation. "
                                "Minst två behövs innan riktning visas."
                            )

                        supply_sales = build_supply_vs_sales_monitor(
                            confirmation_target,
                            supply_history,
                            _load_sold_comp_records(),
                        )
                        if supply_sales.get("status") == "DESKRIPTIV_JÄMFÖRELSE":
                            st.caption(
                                f"Supply vs SOLD: {supply_sales.get('verified_exact_sold_in_window', 0)} "
                                "verifierade exakta försäljningar under supply-perioden."
                            )
                            st.caption(supply_sales.get("observation", ""))
                            st.caption(
                                "Detta är en deskriptiv jämförelse och skapar inte efterfrågesignal, "
                                "scarcity-score, KÖP, marknadsvärde eller maxpris."
                            )
                        elif supply_sales.get("verified_exact_sold_total", 0):
                            st.caption(
                                f"Supply vs SOLD: {supply_sales.get('verified_exact_sold_total', 0)} verifierade "
                                "exakta SOLD finns, men supply-historiken räcker ännu inte för tidsjämförelse."
                            )

                        pressure = build_market_pressure_monitor(
                            confirmation_target,
                            supply_history,
                            _load_sold_comp_records(),
                        )
                        if pressure.get("status") in {"TRE_SERIER_OBSERVERADE", "SUPPLY_OCH_SOLD_OBSERVERAT"}:
                            st.markdown("**Market Pressure – observerade fakta**")
                            st.caption(
                                f"Exact supply: {pressure.get('supply_direction')} "
                                f"({pressure.get('supply_change', 0):+d}) · "
                                f"Verifierade exakta SOLD med pris: {pressure.get('exact_sold_with_price_in_window', 0)}"
                            )
                            if pressure.get("price_direction") != "EJ_BEDÖMBAR":
                                st.caption(
                                    f"SOLD-pris: {pressure.get('price_direction')} · "
                                    f"median {pressure.get('early_median_sek'):.0f} → {pressure.get('late_median_sek'):.0f} kr "
                                    f"({pressure.get('price_change_sek'):+.0f} kr)."
                                )
                            else:
                                st.caption("SOLD-pris: för få verifierade exakta försäljningar för prisriktning.")
                            st.caption(pressure.get("observation", ""))
                            st.caption(
                                "Ingen demand-signal, scarcity-score, marknadstrend, KÖP, värdering eller maxpris skapas av detta."
                            )

                        if confirmation.get("ready") and st.button(
                            f"Spara exact-supply observation – {player} #{card_number}",
                            key=f"save_exact_supply_history_{ei}_{player}_{card_number}",
                        ):
                            snapshot = build_snapshot(confirmation_target, confirmation)
                            saved = save_snapshot(EXACT_SUPPLY_HISTORY_PATH, snapshot)
                            st.success(f"Exact-supply-observation sparad. Historiken innehåller nu {saved} poster totalt.")
                        if exact_creds and st.button(
                            f"Kontrollera Tradera för exakt kort – {player} #{card_number}",
                            key=f"exact_supply_{ei}_{player}_{card_number}",
                        ):
                            with st.spinner("Söker efter kandidater för exakt kortidentitet…"):
                                category_name = "Hockey - NHL" if sport_label == "Hockey" else "Fotboll"
                                supply = verify_exact_query_supply(
                                    exact_item,
                                    app_id=exact_creds[0],
                                    app_key=exact_creds[1],
                                    category_name=category_name,
                                    pages=2,
                                )
                                new_items = supply.get("candidate_items") or []
                                if new_items:
                                    save_expansion_items(SEARCH_EXPANSION_DATA_PATH, new_items)
                                    get_data.clear()
                                    st.session_state["result_cache"] = {}
                                st.info(
                                    f"{supply.get('observed_query_candidates', 0)} unika Tradera-träffar observerades "
                                    f"på {supply.get('pages_checked', 0)} kontrollerade söksidor."
                                )
                                st.caption(supply.get("scope_note", ""))
                                if new_items:
                                    st.caption(
                                        "Träffarna har lagts i kandidatunderlaget och måste nu passera vanlig FlipFynd-analys "
                                        "innan de kan klassas som bekräftad exakt match, möjlig match eller fel kort."
                                    )
                    if not exact_creds:
                        st.info("Exakt Tradera-kontroll aktiveras när säkra Tradera API-uppgifter finns i appens secrets.")

            pressure_queue = build_pressure_research_queue(
                st.session_state.get("results") or [],
                load_history(EXACT_SUPPLY_HISTORY_PATH),
                _load_sold_comp_records(),
                limit=6,
            )
            if pressure_queue.get("rows"):
                with st.expander("🔥 Pressure Research – kort värda extra kontroll", expanded=False):
                    st.caption(
                        "Detta är en manuell researchkö, inte en KÖP-lista. Kort lyfts bara när flera redan "
                        "observerade fakta sammanfaller. Ingen ny score skapas."
                    )
                    pressure_source_map = {}
                    for source_item in st.session_state.get("results") or []:
                        if isinstance(source_item, dict):
                            source_key = exact_identity_key(source_item)
                            if source_key and source_key not in pressure_source_map:
                                pressure_source_map[source_key] = source_item

                    for prow in pressure_queue.get("rows", []):
                        player = prow.get("player_name") or "Okänd spelare"
                        set_name = prow.get("set_name") or "Okänt set"
                        season = prow.get("season") or "?"
                        card_no = prow.get("card_number") or "?"
                        st.write(f"**{player} · {set_name} · {season} · #{card_no}**")
                        st.caption(prow.get("label", ""))
                        facts=[]
                        if prow.get("supply_down"):
                            facts.append(f"exact-supply {prow.get('supply_change', 0):+d}")
                        if prow.get("verified_sold_present"):
                            facts.append(f"{prow.get('exact_sold_with_price_in_window', 0)} verifierade exakta SOLD med pris")
                        if prow.get("observed_sold_price_up"):
                            facts.append(
                                f"observerad SOLD-median {prow.get('early_median_sek'):.0f} → "
                                f"{prow.get('late_median_sek'):.0f} kr"
                            )
                        st.caption(" · ".join(facts) if facts else "Otillräckligt kombinerat underlag")

                        source_item = pressure_source_map.get(prow.get("identity_key"))
                        if source_item:
                            drill = build_pressure_drilldown(
                                source_item,
                                load_history(EXACT_SUPPLY_HISTORY_PATH),
                                _load_sold_comp_records(),
                            )
                            with st.expander(f"Varför lyfts {player} #{card_no}?", expanded=False):
                                st.markdown("**Varför kortet ligger i researchkön**")
                                if drill.get("why"):
                                    for reason in drill.get("why", []):
                                        st.write(f"• {reason.get('text')}")
                                else:
                                    st.caption("Inga starka kombinerade tryckobservationer finns.")

                                st.markdown("**Exact-supply-historik**")
                                if drill.get("supply_snapshots"):
                                    for snap in drill.get("supply_snapshots", [])[-6:]:
                                        st.write(
                                            f"• {snap.get('observed_at')}: "
                                            f"{snap.get('confirmed_exact', 0)} bekräftade exakta, "
                                            f"{snap.get('possible', 0)} möjliga."
                                        )
                                else:
                                    st.caption("Ingen sparad exact-supply-historik.")

                                st.markdown("**Verifierade exakta SOLD i perioden**")
                                if drill.get("sold_evidence"):
                                    for sold_row in drill.get("sold_evidence", [])[-8:]:
                                        st.write(
                                            f"• {sold_row.get('sold_at')}: "
                                            f"{sold_row.get('price_sek', 0):.0f} kr"
                                        )
                                else:
                                    st.caption("Inga verifierade exakta SOLD med pris i supply-perioden.")

                                st.markdown("**Vad saknas innan KÖP ens kan övervägas?**")
                                if drill.get("blockers_before_buy_consideration"):
                                    for blocker in drill.get("blockers_before_buy_consideration", []):
                                        st.write(f"• {blocker}")
                                else:
                                    st.caption(
                                        "Inga av de kontrollerade blockerarna saknas just nu. "
                                        "Det betyder fortfarande inte automatiskt KÖP."
                                    )
                                auto_flow = build_automatic_research_flow(
                                    source_item,
                                    load_history(EXACT_SUPPLY_HISTORY_PATH),
                                    _load_sold_comp_records(),
                                )
                                st.markdown("**Automatisk research**")
                                st.caption(
                                    f"FlipFynd har redan gjort {len(auto_flow.get('auto_completed', []))} säkra kontroller "
                                    "utan extra knapptryckningar."
                                )
                                if auto_flow.get("next_intervention"):
                                    intervention = auto_flow["next_intervention"]
                                    st.info(
                                        f"Enda nästa steget: **{intervention.get('label')}** — "
                                        f"{intervention.get('reason')}"
                                    )
                                    if len(intervention.get("actions", [])) > 1:
                                        with st.expander("Vad behöver verifieras?", expanded=False):
                                            for action in intervention.get("actions", []):
                                                st.write(f"• {action.get('label')}")
                                else:
                                    st.success(
                                        "Alla säkra researchkontroller är klara. Inget extra knapptryck behövs just nu."
                                    )
                                st.caption(auto_flow.get("note", ""))
                                st.caption(drill.get("note", ""))
                    st.caption(
                        "Pressure Research påverkar inte KÖP, marknadsvärde, maxpris, demand-signal eller scarcity-score."
                    )

            market_gap_queue = build_market_gap_queue(st.session_state.get("results") or [], limit=5)
            if market_gap_queue.get("rows"):
                with st.expander("📉 Market Gap – tunt utbud att undersöka", expanded=False):
                    st.caption(
                        "Visar spelare där FlipFynd ser få aktiva kandidater i den aktuella analyserade poolen "
                        "men redan har en efterfrågesignal. Det betyder inte automatiskt fynd eller KÖP."
                    )
                    for gi, grow in enumerate(market_gap_queue.get("rows", [])):
                        st.write(f"**{grow['player_name']}** · {grow['active_candidate_supply']} aktiva kandidater i FlipFynd-poolen")
                        if grow["status"] == "GAP_WITH_MARKET_EVIDENCE":
                            st.caption("Tunt internt utbud + befintligt marknadsunderlag. Ordinarie KÖP-regler gäller fortfarande.")
                        else:
                            st.caption("Researchsignal: tunt internt utbud, men marknadsunderlaget räcker inte för slutsats.")
                        if grow.get("blockers"):
                            st.caption("Kontrollera först: " + " · ".join(grow["blockers"]))
                        for listing in grow.get("listings") or []:
                            st.markdown(f"[Öppna annonsen – {listing['title']}]({listing['url']})")
                        creds = _resolve_tradera_api_credentials()
                        if creds and st.button(
                            f"Kontrollera aktivt Tradera-utbud – {grow['player_name']}",
                            key=f"active_supply_{gi}_{grow['player_name']}",
                        ):
                            with st.spinner("Kontrollerar aktivt utbud via Tradera API…"):
                                category_name = "Hockey - NHL" if sport_label == "Hockey" else "Fotboll"
                                supply = verify_active_supply(
                                    grow, app_id=creds[0], app_key=creds[1],
                                    category_name=category_name, pages=2,
                                )
                                label = classify_verified_supply(supply)
                                st.info(
                                    f"{label}: {supply.get('observed_unique_items', 0)} unika träffar observerades "
                                    f"på {supply.get('pages_checked', 0)} kontrollerade söksidor."
                                )
                                st.caption(supply.get("scope_note", ""))

            lot_treasure_queue = build_lot_treasure_queue(st.session_state.get("results") or [], limit=5)
            if lot_treasure_queue.get("rows"):
                with st.expander("🧰 Lot Treasure – paket värda kort-för-kort-kontroll", expanded=False):
                    st.caption(
                        "Research-kandidater, inte KÖP. FlipFynd prioriterar lotter där befintliga signaler "
                        "gör det rimligt att granska innehållet närmare, men antar aldrig vilka kort som faktiskt ingår."
                    )
                    for lrow in lot_treasure_queue["rows"]:
                        sig = lrow["signal"]
                        st.write(f"**{lrow['title']}** · {sig['label']}")
                        if sig.get("lot_count"):
                            st.caption(f"Identifierat antal kort: {sig['lot_count']}")
                        if sig.get("evidence_types"):
                            st.caption("Research-spår: " + " · ".join(sig["evidence_types"][:5]))
                        if sig.get("reasons"):
                            st.caption("Varför: " + " • ".join(sig["reasons"][:3]))
                        if sig.get("verify_first"):
                            st.caption("Kontrollera först: " + " • ".join(sig["verify_first"][:4]))
                        if lrow.get("url"):
                            st.markdown(f"[Öppna annonsen]({lrow['url']})")
                        st.divider()

            oddity_story_queue = build_oddity_story_queue(st.session_state.get("results") or [], limit=6)
            if oddity_story_queue.get("rows"):
                with st.expander("🧠 Oddity & Story Hunter – märkliga kort som kan vara felbeskrivna", expanded=False):
                    _od_stats = registry_stats()
                    st.caption(f"Kunskapsbas: {_od_stats['seed_cards']} kuraterade seed-kort · {_od_stats['taxonomy_categories']} värdedrivarkategorier. Matchning är researchsignal, inte värdering.")
                    st.caption(
                        "Research-kandidater, inte KÖP. Här letar FlipFynd efter error-/story-/kultkort och andra "
                        "värdedrivare som säljaren kan ha missat. Premie får först räknas när exakt variant och SOLD-data är verifierade."
                    )
                    for orow in oddity_story_queue["rows"]:
                        sig = orow["signal"]
                        st.write(f"**{orow['title']}** · {sig['label']} · prioritet {sig['priority_score']}/100")
                        if sig.get("known_story_matches"):
                            st.caption("Känd referens: " + " · ".join(sig["known_story_matches"]))
                        if sig.get("flags"):
                            st.caption("Spår: " + " · ".join(sig["flags"][:6]))
                        if sig.get("reasons"):
                            st.caption("Varför: " + " • ".join(sig["reasons"][:3]))
                        if sig.get("verify_first"):
                            st.caption("Verifiera först: " + " • ".join(sig["verify_first"][:5]))
                        if orow.get("url"):
                            st.markdown(f"[Öppna annonsen]({orow['url']})")
                        st.divider()

            registry_proposals = build_registry_proposal_queue(st.session_state.get("results") or [], limit=8)
            if registry_proposals.get("rows"):
                with st.expander("🧪 Förslag till Oddity-kunskapsbas – kräver granskning", expanded=False):
                    st.caption(
                        f"{registry_proposals.get('proposal_count', 0)} kandidatposter · "
                        f"{registry_proposals.get('review_ready_count', 0)} redo för manuell källgranskning. "
                        "FlipFynd lägger aldrig själv till poster i registret."
                    )
                    for prow in registry_proposals["rows"]:
                        status_label = {
                            "REVIEW_READY": "🟢 REDO FÖR GRANSKNING",
                            "NEEDS_CORROBORATION": "🟡 BEHÖVER OBEROENDE BEVIS",
                            "NEEDS_EVIDENCE": "⚪ BEHÖVER MER EVIDENS",
                        }.get(prow["status"], prow["status"])
                        st.write(f"**{prow['title']}** · {status_label} · prioritet {prow['priority_score']}/100")
                        if prow.get("categories"):
                            st.caption("Kategori: " + " · ".join(prow["categories"]))
                        st.caption(f"Återkommande observationer: {prow['occurrences']}")
                        if prow.get("evidence"):
                            st.caption("Evidens: " + " • ".join(prow["evidence"][:6]))
                        st.caption("Nästa steg: " + prow["action"])
                        for uidx, url in enumerate(prow.get("urls") or [], start=1):
                            st.markdown(f"[Öppna underlag {uidx}]({url})")
                        st.divider()
                    st.caption(registry_proposals.get("note") or "")

            bad_listing_queue = build_bad_listing_queue(st.session_state.get("results") or [], limit=5)
            if bad_listing_queue.get("rows"):
                with st.expander("🧩 Dåligt beskrivna annonser – kan vara lättare att missa", expanded=False):
                    st.caption(
                        "Detta är annonskvalitets-signaler, inte kortfakta eller nya KÖP. "
                        "FlipFynd pekar ut vad som saknas eller är otydligt så att du kan kontrollera annonsen manuellt."
                    )
                    for brow in bad_listing_queue["rows"]:
                        sig = brow["signal"]
                        st.write(f"**{brow['title']}** · {sig['label']}")
                        if sig.get("traits"):
                            st.caption("Annonsbrister: " + " · ".join(sig["traits"][:5]))
                        if sig.get("reasons"):
                            st.caption("Varför: " + " • ".join(sig["reasons"][:3]))
                        if sig.get("verify_first"):
                            st.caption("Kontrollera först: " + " • ".join(sig["verify_first"][:4]))
                        if brow.get("url"):
                            st.markdown(f"[Öppna annonsen]({brow['url']})")
                        st.divider()

            mispricing_queue = build_mispricing_review_queue(st.session_state.get("results") or [], limit=5)
            if mispricing_queue.get("rows"):
                with st.expander("🕵️ Misstänkt felprissatta – extra kontroll", expanded=False):
                    st.caption(
                        "Research-kandidater, inte nya KÖP. FlipFynd visar varför annonsen kan vara "
                        "underbeskriven/felklassad och vad som måste verifieras."
                    )
                    for mrow in mispricing_queue["rows"]:
                        hyp = mrow["hypothesis"]
                        st.write(f"**{mrow['title']}** · {hyp['headline']}")
                        if hyp.get("hypothesis_types"):
                            st.caption("Spår: " + " · ".join(hyp["hypothesis_types"]))
                        if hyp.get("reasons"):
                            st.caption("Varför: " + " • ".join(hyp["reasons"][:3]))
                        if hyp.get("verify_first"):
                            st.caption("Verifiera först: " + " • ".join(hyp["verify_first"][:4]))
                        if hyp.get("blockers"):
                            st.caption("Saknas för starkare slutsats: " + " • ".join(hyp["blockers"][:3]))
                        if mrow.get("url"):
                            st.markdown(f"[Öppna annonsen]({mrow['url']})")
                        st.divider()

            if _advanced_terminal:
                with st.expander("🔎 Varför blir inget ett verifierat KÖP?", expanded=False):
                    st.caption(
                        "Här ser du exakt hur många annonser som finns kvar efter varje steg. "
                        "Detta är diagnostik för den hårda KÖP-gränsen. Den dynamiska topp 5-listan ovan "
                        "visar fortfarande de bästa kontrollkandidaterna."
                    )
                    stages = funnel.get("stages") or []
                    st.write(" → ".join(f"**{row['count']}** {row['label'].lower()}" for row in stages))

                    d = funnel.get("decisions") or {}
                    d1, d2, d3 = st.columns(3)
                    d1.metric("KÖP", int(d.get("KÖP", 0)))
                    d2.metric("BEVAKA", int(d.get("BEVAKA", 0)))
                    d3.metric("EJ KÖPKLARA", int(d.get("SKIP", 0)))

                    debug_state = st.session_state.get("debug") or {}
                    coverage_added = int(debug_state.get("coverage_diversified_added", 0) or 0)
                    if coverage_added > 0:
                        st.info(
                            f"Urvalet breddades med {coverage_added} kandidat(er) från andra signalprofiler "
                            "så att inte en enda ranking eller samma spelare tar alla djupanalysplatser."
                        )
                    discovery_deepened = int(debug_state.get("discovery_deepened", 0) or 0)
                    if discovery_deepened:
                        st.info(
                            f"Discovery Engine gav {discovery_deepened} kandidat(er) från andra fyndspår "
                            "djupanalys. KÖP-kraven är oförändrade."
                        )
                    if debug_state.get("second_pass_triggered"):
                        st.success(
                            f"FlipFynd gjorde automatiskt ett extra analysvarv på "
                            f"{int(debug_state.get('second_pass_full', 0) or 0)} fler kandidater eftersom första varvet gav 0 KÖP."
                        )

                    biggest = funnel.get("biggest_drop")
                    if biggest and biggest.get("drop", 0) > 0:
                        st.caption(
                            f"Största bortfallet i grundsållningen: {biggest['from']} → {biggest['to']} "
                            f"({biggest['drop']} annonser försvinner där)."
                        )

                    readiness = funnel.get("decision_readiness") or []
                    if readiness:
                        st.markdown("**Beslutsunderlag – var saknas evidens?**")
                        st.caption(
                            "Dessa mått är oberoende evidensgrindar, inte en påhittad sekventiell funnel. "
                            "De visar hur många analyserade annonser som faktiskt har respektive typ av underlag."
                        )
                        rcols = st.columns(min(3, len(readiness)))
                        for idx, row in enumerate(readiness):
                            count = int(row.get("count", 0) or 0)
                            share = float(row.get("share", 0) or 0)
                            rcols[idx % len(rcols)].metric(row.get("label", "Underlag"), count, f"{share:.0%} av analyserade")

                    blockers = funnel.get("blockers") or []
                    if blockers:
                        st.markdown("**Vanligaste skälen till att analyserade kort inte blir KÖP:**")
                        bcols = st.columns(min(3, len(blockers)))
                        for idx, blocker in enumerate(blockers):
                            bcols[idx % len(bcols)].metric(blocker["label"], blocker["count"])

                    primary = funnel.get("primary_reasons") or []
                    if primary:
                        with st.expander("Visa exakta stopporsaker", expanded=False):
                            for row in primary:
                                category = row.get("category") or "Övrigt"
                                st.write(f"• **{row['count']} st · {category}** – {row['reason']}")

                    if stages and stages[-1]["count"] == 0:
                        st.warning(
                            "Inga annonser når själva analysen. Då sitter problemet före köpbedömningen – "
                            "titta på steget där antalet faller till noll."
                        )
                    elif no_buy and stages and stages[-1]["count"] > 0:
                        st.info(
                            "Annonser når analysen, men inget klarar den verifierade KÖP-gränsen. "
                            "Det hindrar inte FlipFynd från att visa de fem bästa UNDERSÖK-kandidaterna ovan."
                        )

            if _advanced_terminal:
                hidden_analysed = [
                    item for item in (st.session_state.get("results") or [])
                    if item not in visible
                ]
                if hidden_analysed:
                    with st.expander(f"Visa fler analyserade kort ({len(hidden_analysed)})", expanded=False):
                        st.caption(
                            "Dessa kort har analyserats men ligger utanför huvudlistan, oftast eftersom de är SKIP "
                            "eller har lägre analyssäkerhet. De är inte fynd bara för att de visas här."
                        )
                        for extra_idx, candidate in enumerate(hidden_analysed[:50], start=1):
                            title = candidate.get("titel") or candidate.get("title") or "Okänd annons"
                            decision = candidate.get("beslut") or candidate.get("decision") or "Ej bedömd"
                            st.write(f"**#{extra_idx} · {title}** · {decision}")
                            url = candidate.get("lank") or candidate.get("url") or candidate.get("link")
                            if url:
                                st.markdown(f"[Öppna annonsen på Tradera ↗]({url})")
                            reason = candidate.get("reason") or candidate.get("decision_reason")
                            if reason:
                                st.caption(str(reason))
                            st.divider()

        st.caption("Behöver du alla interna mått? Slå på ‘Visa fördjupad analys’ ovan.")
        st.stop()

    st.divider()
    non_skip_count = sum(1 for item in st.session_state["results"] if item.get("beslut") != "SKIP")
    if non_skip_count > 0:
        st.subheader(f"Bästa fynden ({len(visible)})")
    else:
        st.subheader(f"Bästa kandidaterna ({len(visible)})")
        if visible:
            analysed_total = int(st.session_state.get("debug", {}).get("final_results", len(st.session_state["results"])) or 0)
            st.info(
                f"🔎 {analysed_total} {sport_label.lower()}annonser analyserade – inget är tillräckligt säkert för KÖP ännu. "
                "Här nedanför visas de kandidater som ligger närmast."
            )
            why = summarize_no_find_reasons(st.session_state["results"])
            if why.get("reasons"):
                st.markdown("### Varför blir det inga KÖP?")
                cols_why = st.columns(min(3, len(why["reasons"])))
                for idx_reason, reason in enumerate(why["reasons"][:6]):
                    with cols_why[idx_reason % len(cols_why)]:
                        st.metric(reason["label"], reason["count"])
                st.caption("Varje annons räknas under sin viktigaste nuvarande spärr. Detta ändrar inte analysen – det förklarar bara den.")

            # Show a short, actionable queue instead of forcing the user to inspect
            # twenty full cards to understand what would need to improve.
            near_buy_rows = []
            for candidate in st.session_state["results"]:
                guidance = build_near_buy_guidance(candidate)
                if guidance.get("readiness_score", 0) <= 0:
                    continue
                near_buy_rows.append((guidance.get("readiness_score", 0), candidate, guidance))
            near_buy_rows.sort(key=lambda row: (row[0], float(row[1].get("deal_score", 0) or 0)), reverse=True)
            if near_buy_rows:
                st.markdown("### 🎯 Närmast KÖP")
                st.caption("Det här är inte köprekommendationer. Här ser du vilka kandidater som ligger närmast och exakt vad som fortfarande stoppar dem.")
                for ready_score, candidate, guidance in near_buy_rows[:5]:
                    with st.container(border=True):
                        top_cols = st.columns([3, 1])
                        top_cols[0].markdown(f"**{candidate.get('titel', 'Okänd annons')}**")
                        top_cols[1].metric("Köpberedskap", f"{ready_score}/100")
                        st.markdown(f"**{guidance.get('status', 'GRANSKA')}** – {guidance.get('primary_action', '')}")
                        steps = guidance.get("next_steps") or []
                        if steps:
                            st.caption("Nästa steg: " + " • ".join(steps[:3]))
                        economics = []
                        if candidate.get("net_profit_estimate") is not None:
                            economics.append(f"nettovinst {float(candidate.get('net_profit_estimate') or 0):.0f} kr")
                        if candidate.get("roi_estimate") is not None:
                            economics.append(f"ROI {float(candidate.get('roi_estimate') or 0):.0%}")
                        if candidate.get("sale_probability") is not None:
                            economics.append(f"säljchans {float(candidate.get('sale_probability') or 0):.0f}%")
                        if economics:
                            st.caption("Nu: " + " · ".join(economics))
                        if candidate.get("lank"):
                            st.markdown(f"[Öppna annonsen på Tradera ↗]({candidate.get('lank')})")

    if not visible:
        if not data:
            st.warning(
                "Inga annonser är inlästa ännu. Hämta annonser från Tradera först – dina filter är inte problemet."
            )
        elif st.session_state.get("debug", {}).get("final_results", 0) == 0:
            st.warning(
                "FlipFynd hittade inga analyserbara kandidater med den här kombinationen. Du gör inte nödvändigtvis något fel. Börja med tom sökruta, Annonsform = Alla och inga specialfilter. Öppna sållningen nedan för att se exakt vilket steg som tar bort annonserna."
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

    # Opportunity Radar 2.0: only surface listings that are actually worth time.
    radar_groups = {name: [] for name in ("AGERA NU", "BEVAKA", "NÄRA FYND", "BEHÖVER VERIFIERAS")}
    for candidate in filtered:
        action = candidate.get("opportunity_action", "IGNORERA")
        deal = float(candidate.get("deal_score", 0) or 0)
        identity_status = candidate.get("exact_identity_gate_status")
        if action == "AGERA NU" and deal >= 40:
            radar_groups["AGERA NU"].append(candidate)
        elif action == "BEVAKA" and deal >= 25:
            radar_groups["BEVAKA"].append(candidate)
        elif deal >= 20:
            radar_groups["NÄRA FYND"].append(candidate)
        elif candidate.get("visual_verification_required") or identity_status in {"LÅST", "GRANSKA"}:
            radar_groups["BEHÖVER VERIFIERAS"].append(candidate)

    for group in radar_groups.values():
        group.sort(key=lambda x: (x.get("opportunity_priority_score", 0), x.get("deal_score", 0)), reverse=True)

    radar_main = radar_groups["AGERA NU"] + radar_groups["BEVAKA"] + radar_groups["NÄRA FYND"]
    radar_main.sort(key=lambda x: (x.get("opportunity_priority_score", 0), x.get("deal_score", 0)), reverse=True)

    best_buy = build_best_buy_decision_card(filtered)
    st.subheader("🎯 Ditt beslut just nu")
    st.caption("Börja här. FlipFynd visar bara ett köp när underlaget räcker; annars är rätt beslut att avstå eller bevaka.")
    if best_buy["status"] == "READY":
        bc = best_buy["card"]
        st.success(f"### KÖP · {bc['title']}")
        b1, b2, b3, b4, b5 = st.columns(5)
        b1.metric("Kostar nu", f"{bc['total_cost']:.0f} kr")
        b2.metric(bc.get("shipping_label") or ("Frakt" if bc.get("shipping_known") else "Antagen frakt"), f"{bc['shipping']:.0f} kr" if bc.get("shipping") is not None else "Ej säkert")
        b3.metric("Uppskattat marknadsvärde", f"{bc['expected_resale']:.0f} kr" if bc["expected_resale"] is not None else "Otillräckligt underlag")
        b4.metric("Betala högst", f"{bc['max_total_price']:.0f} kr" if bc["max_total_price"] is not None else "Ej säkert")
        b5.metric("Möjlig nettovinst", f"+{bc['net_profit']:.0f} kr" if bc['net_profit'] >= 0 else f"{bc['net_profit']:.0f} kr")
        simple=[]
        if bc["expected_days"] is not None: simple.append(f"verifierad säljtid ~{bc['expected_days']:.0f} dagar")
        simple.append("exakt kortidentitet verifierad")
        st.caption(" · ".join(simple))
        if bc["url"]:
            st.markdown(f"**[Öppna annonsen på Tradera ↗]({bc['url']})**")
        with st.expander("Visa varför FlipFynd väljer detta kort", expanded=False):
            if bc["reasons"]:
                st.write(" • ".join(bc["reasons"]))
            if bc["floor_profit"] is not None:
                st.write(f"Svagare dokumenterat utfall: {bc['floor_profit']:+.0f} kr i beräknad nettovinst.")
            st.caption(best_buy["note"])
    else:
        st.info("**KÖP INGET JUST NU.** FlipFynd hittar inget kort med tillräckligt starkt underlag för ett säkert förstaval.")
        st.caption(best_buy["note"])
        fallback = build_best_available_view(st.session_state.get("results") or [], limit=3)
        if fallback.get("status") == "READY":
            with st.expander("Visa de 3 bästa alternativen trots att inget är KÖP", expanded=False):
                st.caption(fallback.get("note") or "")
                for rank, row in enumerate(fallback.get("rows") or [], start=1):
                    st.markdown(f"**#{rank} · {row['title']} · {row.get('decision') or 'EJ BESLUT'}**")
                    market_value_text = f"{float(row['market_value']):.0f} kr" if row.get("market_value") is not None else "Otillräckligt underlag"
                    st.caption(f"Uppskattat marknadsvärde: {market_value_text}")
                    if row.get("primary_blocker"):
                        st.caption("Stoppar KÖP: " + str(row["primary_blocker"]))
                    if row.get("url"):
                        st.markdown(f"[Öppna annonsen ↗]({row['url']})")

    buy_queue = build_top_buy_queue(filtered)
    if buy_queue["status"] == "READY" and len(buy_queue.get("picks", [])) > 1:
        st.markdown("### Två alternativ")
        alt_cols = st.columns(min(2, len(buy_queue["picks"][1:3])))
        for alt_idx, pick in enumerate(buy_queue["picks"][1:3]):
            with alt_cols[alt_idx]:
                with st.container(border=True):
                    st.markdown(f"**#{pick['rank']} {pick['title']}**")
                    st.write(f"Kostar {pick['total_cost']:.0f} kr · möjlig vinst {pick['net_profit']:+.0f} kr")
                    if pick["max_total_price"] is not None:
                        st.caption(f"Betala högst {pick['max_total_price']:.0f} kr totalt")
                    if pick["url"]:
                        st.markdown(f"[Öppna annonsen ↗]({pick['url']})")

    top3_compare = build_top_buy_decision_compare(buy_queue, filtered)
    if top3_compare["status"] == "READY":
        st.subheader("🔬 Fördjupad jämförelse av Top 3")
        st.caption(top3_compare["note"])
        for row in top3_compare["rows"]:
            with st.container(border=True):
                st.markdown(f"**#{row['rank']} · {row['title']}**")
                c1,c2,c3,c4=st.columns(4)
                c1.metric("Kapital", f"{row['capital_tied']:.0f} kr")
                c2.metric("Svagt utfall", f"{row['weak_profit']:+.0f} kr" if row["weak_profit"] is not None else "Ej säkert")
                c3.metric("Troligt utfall", f"{row['likely_profit']:+.0f} kr")
                if row["sellability_score"] is not None:
                    c4.metric("Säljbarhet", f"{row['sellability_score']:.0f}/100")
                else:
                    c4.metric("Säljbarhet", "Otillräckligt underlag")
                detail=[]
                if row["weak_roi_pct"] is not None: detail.append(f"svag ROI {row['weak_roi_pct']:+.0f}%")
                detail.append(f"trolig ROI {row['likely_roi_pct']:+.0f}%")
                if row["verified_sell_days"] is not None: detail.append(f"verifierad säljtid ~{row['verified_sell_days']:.0f} d")
                if row["sellability_label"]: detail.append(str(row["sellability_label"]))
                if row["capital_efficiency_score"] is not None: detail.append(f"kapitalpoäng {row['capital_efficiency_score']:.0f}/100")
                st.caption(" · ".join(detail))
                turnover=row.get("turnover")
                if turnover:
                    st.caption(
                        f"♻️ Kapitalomlopp: {turnover['cycles_30d']:.2f} varv/30 d · "
                        f"{turnover['profit_30d']:+.0f} kr vinst/30 d · "
                        f"{turnover['roi_30d_pct']:+.0f}% ROI/30 d"
                    )
                    st.caption(turnover["note"])
                else:
                    st.caption("♻️ Kapitalomlopp: otillräckligt underlag – verifierad sold-velocity saknas.")
                if row["url"]: st.markdown(f"[Öppna annonsen på Tradera]({row['url']})")

    queue_risk_reward = build_queue_risk_reward(buy_queue, filtered)
    rr_by_rank = {r["rank"]: r["risk_reward"] for r in queue_risk_reward["rows"]}
    decision_summary = build_buy_decision_summary(buy_queue, filtered)
    buy_timing = build_queue_buy_timing(buy_queue, filtered)
    timing_by_rank = {r["rank"]: r["timing"] for r in buy_timing["rows"]}
    price_targets = build_queue_price_drop_targets(buy_queue, filtered, buy_timing["rows"])
    target_by_rank = {r["rank"]: r["target"] for r in price_targets["rows"]}
    opportunity_gaps = build_queue_opportunity_gaps(buy_queue, filtered, buy_timing["rows"], price_targets["rows"])
    gap_by_rank = {r["rank"]: r["gap"] for r in opportunity_gaps["rows"]}
    watch_priority = build_watch_priority_queue(buy_queue, filtered, buy_timing["rows"], opportunity_gaps["rows"])
    watch_by_rank = {r["rank"]: r["watch"] for r in watch_priority["rows"]}
    if decision_summary["status"] == "READY":
        st.subheader("🔬 Pris- och timingdetaljer")
        for row in decision_summary["rows"]:
            max_text = f"{row['max_total']:.0f} kr" if row["max_total"] is not None else "ej säkert"
            down_text = f"{row['downside_profit']:+.0f} kr" if row["downside_profit"] is not None else "ej säkert"
            days_text = f"{row['expected_days']:.0f} d" if row["expected_days"] is not None else "otillräckligt underlag"
            timing = timing_by_rank.get(row["rank"], {})
            action = timing.get("action")
            if action == "INOM MAXPRIS":
                st.success(f"**INOM MAXPRIS · #{row['rank']} {row['title']}**")
            elif action == "ÖVER MAXPRIS":
                st.warning(f"**ÖVER MAXPRIS · #{row['rank']} {row['title']}**")
            else:
                st.info(f"**BEVAKA · #{row['rank']} {row['title']}**")
            st.write(
                f"köp {row['buy_total']:.0f} kr → max {max_text} → "
                f"trolig vinst {row['likely_profit']:+.0f} kr → nedsida {down_text} → säljtid {days_text}"
            )
            if timing.get("reason"):
                st.caption(timing["reason"])
            target = target_by_rank.get(row["rank"], {})
            if target.get("status") == "READY":
                target_text = f"Befintligt maxpris: {target['target_total']:.0f} kr"
                if target.get("target_item_price") is not None:
                    target_text += f" (annonspris ca {target['target_item_price']:.0f} kr + frakt)"
                if target.get("drop_needed") is not None and target.get("drop_needed") > 0:
                    target_text += f" · behövs ca {target['drop_needed']:.0f} kr lägre"
                st.caption("🎯 " + target_text)
            gap = gap_by_rank.get(row["rank"], {})
            if gap.get("status") == "READY":
                extra = f" · #{gap['wait_rank']} bland vänta-korten" if gap.get("wait_rank") is not None else ""
                pct = f" / {gap['gap_pct']:.1f}%" if gap.get("gap_pct") is not None else ""
                st.caption(f"📉 {gap['band']}: {gap['gap_kr']:.0f} kr{pct} från köp{extra}")
            watch = watch_by_rank.get(row["rank"], {})
            if watch.get("status") == "READY":
                st.caption(
                    f"👀 {watch['label']} · bevakningspoäng {watch['score']:.0f}/100"
                    f" · ROI {watch['roi_pct']:.0f}%"
                    + (f" · kapitalpoäng {watch['capital_score']:.0f}" if watch.get("capital_score") is not None else "")
                )
            if row["url"]:
                st.markdown(f"[Öppna annonsen]({row['url']})")
        st.caption(decision_summary["note"])

    if watch_priority["ready"]:
        with st.expander("👀 Bevakningsprioritet – vilka väntelägen är viktigast?", expanded=False):
            for row in watch_priority["ready"]:
                w=row["watch"]
                pct=f"{w['gap_pct']:.1f}%" if w.get("gap_pct") is not None else "ej säkert"
                st.write(
                    f"**#{w['watch_rank']} {row['title']}** · {w['label']} · "
                    f"{w['gap_kr']:.0f} kr / {pct} från köp · "
                    f"möjlig vinst {w['profit']:+.0f} kr"
                )
                if row.get("url"):
                    st.markdown(f"[Öppna annonsen]({row['url']})")
            st.caption("Bevakningsprioriteten är separat från ordinarie KÖP-ranking och skapar inga nya köpbeslut.")

    with st.expander("🔬 Visa full köpordning och analys", expanded=False):
        st.caption(buy_queue["note"])
        if buy_queue["status"] != "READY":
            st.info("Det finns inte tillräckligt säkra KÖP för en köpordning just nu.")
        else:
            medals={1:"🥇",2:"🥈",3:"🥉"}
            for pick in buy_queue["picks"]:
                st.write(f"**{medals.get(pick['rank'],'•')} #{pick['rank']} {pick['title']}**")
                q1,q2,q3=st.columns(3)
                q1.metric("Totalt",f"{pick['total_cost']:.0f} kr")
                q2.metric("Möjlig vinst",f"{pick['net_profit']:.0f} kr")
                q3.metric("Kapitalpoäng",f"{pick['capital_score']:.0f}/100")
                detail=[]
                if pick["expected_days"] is not None: detail.append(f"ca {pick['expected_days']:.0f} dagar")
                if pick["profit_30d"] is not None: detail.append(f"{pick['profit_30d']:.0f} kr/30 dagar")
                if pick["max_total_price"] is not None: detail.append(f"max {pick['max_total_price']:.0f} kr totalt")
                if detail: st.caption(" · ".join(detail))
                rr = rr_by_rank.get(pick["rank"], {})
                if rr.get("status") == "READY":
                    parts=[]
                    if rr.get("weak_profit") is not None: parts.append(f"svagt {rr['weak_profit']:+.0f} kr")
                    if rr.get("likely_profit") is not None: parts.append(f"troligt {rr['likely_profit']:+.0f} kr")
                    if rr.get("strong_resale") is not None: parts.append(f"starkt säljpris {rr['strong_resale']:.0f} kr")
                    if parts: st.caption(" · ".join(parts))
                    if rr.get("capital_downside_pct") is not None:
                        st.caption(f"Kapitalnedsida i svagt scenario: {rr['capital_downside_pct']:.1f}%")
                    st.caption("Risk visas numeriskt. FlipFynd sätter inte låg/medel/hög kapitalrisk utan empiriskt stöd.")
                if pick["why_ahead"]: st.caption("Varför före nästa: " + " • ".join(pick["why_ahead"]))
                if pick["url"]: st.markdown(f"[Öppna på Tradera]({pick['url']})")
                if pick["rank"] < len(buy_queue["picks"]): st.divider()

    with st.expander("💰 Mina pengar – fördela en köpbudget", expanded=False):
        st.caption("FlipFynd väljer bara bland kort som redan är KÖP och har verifierad kapitalpoäng. Den skapar inga nya köpbeslut.")
        portfolio_budget = st.number_input(
            "Budget att använda", min_value=100, max_value=100000, value=2000, step=100,
            key="portfolio_budget",
        )
        portfolio = build_budget_portfolio(filtered, portfolio_budget)
        if portfolio.get("status") == "READY":
            pc1, pc2, pc3 = st.columns(3)
            pc1.metric("Föreslaget köp", f"{portfolio['spent']:.0f} kr")
            pc2.metric("Möjlig nettovinst", f"{portfolio['expected_profit']:.0f} kr")
            pc3.metric("Kvar", f"{portfolio['remaining']:.0f} kr")
            st.caption(
                f"Kapital använt: {portfolio['capital_usage_pct']:.0f}% · "
                f"Vinsttakt från verifierad säljtakt: {portfolio['profit_30d']:.0f} kr/30 dagar · "
                f"ROI/30 d: {portfolio['roi_30d_pct']:.0f}%"
            )
            st.caption(
                f"Svagt scenario för kombinationen: {portfolio['floor_profit']:+.0f} kr · "
                f"{portfolio['evaluated_combination_count']} möjliga verifierade kombinationer jämförda."
            )
            for n, pick in enumerate(portfolio["selected"], 1):
                ce = pick.get("capital_efficiency") or {}
                cost = float(pick.get("total_cost") or pick.get("analysis_total_cost") or 0)
                st.write(f"**{n}. {pick.get('titel', 'Okänt kort')} – {cost:.0f} kr**")
                st.caption(
                    f"{ce.get('label', 'Ej bedömd')} · möjlig nettovinst "
                    f"{float(pick.get('net_profit_estimate') or 0):.0f} kr · "
                    f"kapitalpoäng {float(ce.get('score') or 0):.0f}/100"
                )
                if pick.get("lank"):
                    st.markdown(f"[Öppna på Tradera]({pick.get('lank')})")
            stress=build_portfolio_downside_stress(portfolio.get("selected") or [], budget=portfolio_budget)
            if stress.get("status")=="READY":
                st.markdown("#### 🧯 Portföljens nedsidestest")
                s1,s2,s3=st.columns(3)
                s1.metric("Troligt utfall · hela korgen", f"{stress['likely_portfolio_profit']:+.0f} kr")
                s2.metric("Alla på floor", f"{stress['all_floor_portfolio_profit']:+.0f} kr")
                s3.metric("Försämring mot troligt", f"-{stress['all_floor_damage_vs_likely']:.0f} kr")
                if stress["all_floor_capital_loss"] > 0:
                    st.caption(
                        f"Om samtliga kort samtidigt landar på sina dokumenterade floor-utfall blir "
                        f"portföljförlusten {stress['all_floor_capital_loss']:.0f} kr "
                        f"({stress['all_floor_loss_pct_of_spent']:.1f}% av bundet kapital)."
                    )
                else:
                    st.caption("Även om samtliga valda kort samtidigt når sina dokumenterade floor-utfall är den summerade nettovinsten inte negativ.")
                largest=stress.get("largest_capital_position") or {}
                if largest:
                    st.caption(
                        f"Största kapitalposition: {largest.get('title')} · {largest.get('cost',0):.0f} kr · "
                        f"{largest.get('share_of_selected_capital_pct',0):.1f}% av valt kapital."
                    )
                shocks=stress.get("single_card_shocks") or []
                if shocks:
                    with st.expander("Vilket enskilt kort skadar korgen mest?", expanded=False):
                        for shock in shocks:
                            st.write(
                                f"**{shock['title']} på floor:** korgen {shock['portfolio_profit']:+.0f} kr · "
                                f"försämring {shock['damage_vs_likely']:.0f} kr"
                            )
                st.caption(stress.get("note"))

            opportunity=build_portfolio_opportunity_cost(portfolio, filtered)
            if opportunity.get("status")=="READY":
                st.markdown("#### ⏳ Opportunity cost")
                st.caption(opportunity.get("reserve_note"))
                slow=opportunity.get("slowest_selected")
                if slow:
                    st.caption(
                        f"Långsammast kapital i vald korg: {slow['title']} · "
                        f"{slow['profit_30d']:.0f} kr/30 d på {slow['cost']:.0f} kr · "
                        f"{slow['profit_30d_per_100_capital']:.1f} kr/30 d per 100 kr bundet."
                    )
                alt_costs=opportunity.get("alternative_portfolios") or []
                if alt_costs:
                    with st.expander("Vad kostar de alternativa korgarna i vinsttakt?", expanded=False):
                        for alt in alt_costs:
                            names=", ".join(alt["titles"])
                            st.write(
                                f"**{names}** · {alt['profit_30d']:.0f} kr/30 d · "
                                f"offrar {alt['profit_30d_sacrificed']:.0f} kr/30 d mot vald korg"
                            )
                st.caption(opportunity.get("note"))

            concentration=build_portfolio_concentration(portfolio.get("selected") or [])
            if concentration.get("status")=="READY":
                st.markdown("#### 🧩 Koncentration i köpkorgen")
                c1,c2,c3=st.columns(3)
                c1.metric("Största position", f"{concentration['largest_position_share_pct']:.1f}%")
                c2.metric("Två största", f"{concentration['top_two_position_share_pct']:.1f}%")
                c3.metric("Kort i korgen", f"{concentration['card_count']}")
                with st.expander("Visa kapital per spelare, set och sport", expanded=False):
                    st.markdown("**Spelare**")
                    for group in concentration["player_groups"]:
                        st.write(f"{group['label']}: {group['capital']:.0f} kr · {group['capital_share_pct']:.1f}% · {group['card_count']} kort")
                    st.markdown("**Set/program**")
                    for group in concentration["set_groups"]:
                        st.write(f"{group['label']}: {group['capital']:.0f} kr · {group['capital_share_pct']:.1f}% · {group['card_count']} kort")
                    st.markdown("**Sport**")
                    for group in concentration["sport_groups"]:
                        st.write(f"{group['label']}: {group['capital']:.0f} kr · {group['capital_share_pct']:.1f}% · {group['card_count']} kort")
                    st.markdown("**Enskilda kapitalpositioner**")
                    for pos in concentration["positions"]:
                        st.write(f"{pos['title']}: {pos['cost']:.0f} kr · {pos['capital_share_pct']:.1f}%")
                if concentration.get("unknown_player_capital_pct",0)>0 or concentration.get("unknown_set_capital_pct",0)>0:
                    st.caption(
                        f"Okänd identitet står för {concentration.get('unknown_player_capital_pct',0):.1f}% av kapitalet på spelarnivå "
                        f"och {concentration.get('unknown_set_capital_pct',0):.1f}% på set/programnivå."
                    )
                st.caption(concentration.get("note"))

            identity_integrity=build_portfolio_identity_integrity(portfolio.get("selected") or [])
            if identity_integrity.get("status")=="READY":
                st.markdown("#### 🪪 Identitetsintegritet i köpkorgen")
                i1,i2,i3=st.columns(3)
                i1.metric("Exact comp-sökbar", f"{identity_integrity['exact_comp_search_capital_pct']:.1f}%")
                i2.metric("Beslutsstarkt maxbud", f"{identity_integrity['dynamic_max_bid_capital_pct']:.1f}%")
                i3.metric("Olöst identitet", f"{identity_integrity['unresolved_identity_capital_pct']:.1f}%")
                with st.expander("Visa identitetsnivå per kapitalandel", expanded=False):
                    for group in identity_integrity["identity_groups"]:
                        st.write(
                            f"**{group['status']}**: {group['capital']:.0f} kr · "
                            f"{group['capital_share_pct']:.1f}% · {group['card_count']} kort"
                        )
                    st.markdown("**Kort för kort**")
                    for row in identity_integrity["details"]:
                        score_text="ej satt" if row["identity_score"] is None else f"{row['identity_score']:.0f}/100"
                        permissions=[]
                        if row["supports_exact_comp_search"]: permissions.append("Exact comps")
                        if row["supports_dynamic_max_bid"]: permissions.append("dynamiskt maxbud")
                        permission_text=", ".join(permissions) if permissions else "ingen exact-behörighet"
                        st.write(
                            f"{row['title']}: {row['cost']:.0f} kr · {row['capital_share_pct']:.1f}% · "
                            f"{row['identity_status']} · {score_text} · {permission_text}"
                        )
                st.caption(identity_integrity.get("note"))

            alternatives=portfolio.get("alternatives") or []
            if alternatives:
                with st.expander("Visa alternativa kapitalfördelningar", expanded=False):
                    for i, alt in enumerate(alternatives, 1):
                        names=", ".join(str(x.get("titel") or "Okänt kort") for x in alt["selected"])
                        st.write(
                            f"**Alt {i}: {names}** · {alt['spent']:.0f} kr bundet · "
                            f"{alt['profit_30d']:.0f} kr/30 d · svagt {alt['floor_profit']:+.0f} kr"
                        )
            st.caption("Urvalsordning: " + " → ".join(portfolio.get("selection_basis") or []))
            st.warning("Detta är en budgetfördelning, inte en garanti. Outnyttjad budget är tillåten; FlipFynd fyller inte kapital med svagare eller overifierade köp.")
        else:
            st.info(portfolio.get("note") or "Det finns ännu inte tillräckligt säkra kandidater för en budgetfördelning.")

    # Stjärnskott Radar: research context, collapsed in the novice-first UI.
    with st.expander("🌟 Research: Stjärnskott Radar", expanded=False):
        st.caption("För dig som vill leta spelare vars situation nyligen har förändrats. Detta påverkar aldrig köpbeslutet automatiskt.")
        st.caption("Upptäcker dokumenterade förändringar runt spelare och kopplar dem till redan skannade kort. Momentum ändrar aldrig KÖP, värdering eller maxbud.")
        momentum_upload = st.file_uploader("Läs in momentum-evidens (JSON)", type=["json"], key="momentum_evidence_json", help="JSON-lista med strukturerade poster: player_name, event_type, source_name, source_url, occurred_at och source_type.")
        momentum_events=[]
        if momentum_upload is not None:
            try:
                raw_momentum=json.load(momentum_upload)
                if isinstance(raw_momentum,dict): raw_momentum=raw_momentum.get("records") or raw_momentum.get("events") or []
                intake=ingest_momentum_records(raw_momentum if isinstance(raw_momentum,list) else [])
                momentum_events=intake.get("accepted") or []
                if intake.get("rejected_count"):
                    st.warning(f"{intake['rejected_count']} momentumposter avvisades eftersom evidensen var ofullständig eller källtypen inte stöds.")
            except Exception:
                st.error("Momentumfilen kunde inte läsas som giltig strukturerad JSON. Ingen data har antagits.")
        starshot=build_starshot_radar(momentum_events, filtered)
        if not starshot.get("players"):
            st.info("Ingen verifierad momentum-evidens är inläst ännu. Radarn visar hellre tomt än gissar vilka spelare som är stjärnskott.")
        else:
            sm1,sm2=st.columns(2)
            sm1.metric("Spelare med dokumenterad förändring", starshot["player_count"])
            sm2.metric("Kopplade skannade kort", starshot["matched_card_count"])
            for player in starshot["players"][:10]:
                with st.expander(f"🔥 {player['player_name']} · {player.get('sport') or 'Sport ej angiven'} · {player['event_count']} händelse(r)", expanded=bool(player.get("cards"))):
                    st.write("**Vad har hänt?**")
                    for event in player.get("events",[])[:5]:
                        detail=f" · {event.get('detail')}" if event.get('detail') else ""
                        st.write(f"{event['event_type']} · {event['occurred_at'][:10]} · {event['source_name']}{detail}")
                        st.caption(event.get("source_url"))
                    st.caption(f"Oberoende källor: {player['source_count']} · Händelsetyper: {player['event_type_count']}")
                    st.write("**Kort på marknaden**")
                    if not player.get("cards"):
                        st.info("Inga redan skannade annonser med strukturerat player_name matchar spelaren.")
                    for card in player.get("cards",[])[:8]:
                        cost="okänd" if card.get("total_cost") is None else f"{card['total_cost']:.0f} kr"
                        st.write(f"**{card['title']}** · {card['existing_decision']} · total kostnad {cost}")
                        st.caption(f"Identitet: {card['identity_status']} · Exact SOLD comps: {card['exact_sold_comp_count']} · Sellability: {card.get('sellability') or 'ej verifierad'}")
                        if card.get("url"): st.markdown(f"[Öppna annons]({card['url']})")
                    st.warning(f"{player['market_reaction_status']} — {player['market_reaction_reason']}")
                    st.caption("Stjärnskott ≠ KÖP. Kortets befintliga FlipFynd-bedömning står kvar.")
    st.divider()

    if radar_main or radar_groups["BEHÖVER VERIFIERAS"]:
        st.subheader("📡 Opportunity Radar")
        st.caption("Här visas bara sådant som faktiskt förtjänar din tid. Osäkra kort ligger separat som verifieringsjobb och presenteras inte som fynd.")
        cols = st.columns(4)
        cols[0].metric("🚨 Agera nu", len(radar_groups["AGERA NU"]))
        cols[1].metric("👀 Bevaka", len(radar_groups["BEVAKA"]))
        cols[2].metric("🟠 Nära fynd", len(radar_groups["NÄRA FYND"]))
        cols[3].metric("🔎 Verifiera", len(radar_groups["BEHÖVER VERIFIERAS"]))

        for candidate in radar_main[:6]:
            if candidate in radar_groups["AGERA NU"]:
                label = "AGERA NU"
            elif candidate in radar_groups["BEVAKA"]:
                label = "BEVAKA"
            else:
                label = "NÄRA FYND"
            risk = candidate.get("risk_score")
            risk_text = "ej bedömd" if (risk in (None, 0) and float(candidate.get("deal_score", 0) or 0) == 0) else f"{float(risk or 0):.0f}/100"
            st.write(f"**{label} · {candidate.get('titel', 'Okänd annons')}**")
            st.caption(
                f"Prioritet {candidate.get('opportunity_priority_score', 0):.0f}/100 · "
                f"Fyndpoäng {candidate.get('deal_score', 0):.0f}/100 · Risk {risk_text}"
            )
            if candidate.get("opportunity_reasons"):
                st.caption(" • ".join(candidate.get("opportunity_reasons")[:2]))
            if candidate.get("lank"):
                st.markdown(f"[Öppna på Tradera]({candidate.get('lank')})")

        verification = radar_groups["BEHÖVER VERIFIERAS"]
        if verification:
            with st.expander(f"🔎 Behöver verifieras ({len(verification)})", expanded=False):
                st.caption("Detta är inte fynd. De ligger här endast för att kortidentiteten eller bilderna kan behöva kontrolleras.")
                for candidate in verification[:8]:
                    st.write(f"**{candidate.get('titel', 'Okänd annons')}**")
                    reason = (candidate.get("opportunity_reasons") or candidate.get("visual_edge_reasons") or ["Otillräckligt underlag"])[0]
                    st.caption(reason)
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
                "Bildgranskaren analyserar nu upp till åtta annonsfoton tillsammans, redovisar varje bild och använder fram-/baksida, närbilder och slab-etikett för säkrare kortidentitet. "
                "Den rapporterar bara visuella hypoteser; de påverkar aldrig värdering eller maxbud automatiskt."
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
                    if st.button("🔬 Analysera bilderna", key="btn_" + detective_key):
                        with st.spinner("Granskar fram-/baksida, text, variant och fotokvalitet …"):
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
                            identity = detective.get("identity", comp.get("identity", {}))
                            purchase_safety = detective.get("purchase_safety") or {}
                            st.markdown(
                                f"**Visual Card Detective:** {comp.get('status', 'Granskad')} · "
                                f"säkerhet {comp.get('confidence', 0):.0f}/100 · "
                                f"{identity.get('status', 'Bildidentitet')} {identity.get('score', 0)}/100"
                            )
                            st.caption(
                                f"Analyserade bilder: {detective.get('images_analyzed', 0)} · "
                                f"foto: {findings.get('photo_quality', 'unknown')} · "
                                f"fram: {findings.get('front_visible', 'unknown')} · "
                                f"baksida: {findings.get('back_visible', 'unknown')}"
                            )
                            if purchase_safety:
                                if purchase_safety.get("safe_for_purchase_review"):
                                    st.success(purchase_safety.get("status"))
                                else:
                                    st.error(purchase_safety.get("status"))
                                for blocker in purchase_safety.get("blockers", [])[:4]:
                                    st.caption("⛔ " + blocker)
                                for warning in purchase_safety.get("warnings", [])[:3]:
                                    st.caption("⚠️ " + warning)
                            per_image = findings.get("per_image_observations") or []
                            if per_image:
                                with st.expander("Granskning bild för bild", expanded=False):
                                    for image_row in per_image:
                                        st.caption(
                                            f"Bild {image_row.get('image_index')} · {image_row.get('view')} · "
                                            f"{image_row.get('quality')} — {image_row.get('observation')}"
                                        )
                            visual_bits = []
                            for label, key_name in [
                                ("Spelare", "player_name"), ("Lag/klubb", "team_or_club"),
                                ("Set", "set_or_product"), ("År", "season_or_year"),
                                ("Kortnr", "card_number"), ("Variant", "parallel_or_variant")
                            ]:
                                if findings.get(key_name):
                                    visual_bits.append(f"{label}: {findings.get(key_name)}")
                            if visual_bits:
                                st.caption("🪪 " + " · ".join(visual_bits[:6]))
                            if findings.get("serial_numerator") and findings.get("serial_denominator"):
                                st.caption(f"🔢 Synlig serialisering: {findings.get('serial_numerator')}/{findings.get('serial_denominator')}")
                            if findings.get("condition_clues"):
                                st.caption("🧪 Synligt skick: " + " • ".join(findings.get("condition_clues")[:3]))
                            for discovery in comp.get("discoveries", [])[:5]:
                                st.caption("🔎 " + discovery)
                            for conflict in comp.get("conflicts", [])[:3]:
                                st.caption("⚠️ " + conflict)
                            if identity.get("missing_fields"):
                                st.caption("Saknas visuellt: " + " • ".join(identity.get("missing_fields")[:5]))
                            if identity.get("recommended_next_photo"):
                                st.info("📸 Nästa bästa foto: " + str(identity.get("recommended_next_photo")))

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

                            visual_oddity = build_visual_oddity_signal(
                                findings,
                                title=candidate.get("titel", ""),
                                sport=candidate.get("sport") or candidate.get("kategori") or "",
                            )
                            if visual_oddity.get("candidate") or visual_oddity.get("ordinary_damage_only"):
                                st.markdown(f"**🧬 Visuell Oddity Detector:** {visual_oddity.get('status')} · säkerhet {visual_oddity.get('confidence', 0):.0f}/100")
                                if visual_oddity.get("category_labels"):
                                    st.caption("Möjliga mekanismer: " + " • ".join(visual_oddity.get("category_labels")[:5]))
                                for reason in visual_oddity.get("reasons", [])[:4]:
                                    st.caption("🔎 " + reason)
                                if visual_oddity.get("known_registry_matches"):
                                    st.caption("📚 Registermatch: " + " • ".join(visual_oddity.get("known_registry_matches")[:3]))
                                if visual_oddity.get("verify_first"):
                                    with st.expander("Vad måste verifieras innan detta kan påverka värdet?", expanded=False):
                                        for step in visual_oddity.get("verify_first")[:6]:
                                            st.write("• " + str(step))
                                st.caption(visual_oddity.get("note", ""))

                            reference_check = verify_against_reference_traits(
                                findings,
                                title=candidate.get("titel", ""),
                                sport=candidate.get("sport") or candidate.get("kategori") or "",
                            )
                            if reference_check.get("matches"):
                                st.markdown(
                                    f"**🪞 Referensbild-kontroll:** {reference_check.get('status')} · "
                                    f"match {reference_check.get('best_score', 0):.0f}/100"
                                )
                                for refmatch in reference_check.get("matches", [])[:2]:
                                    st.caption(f"📚 {refmatch.get('title')} · {refmatch.get('status')}")
                                    with st.expander("A/B/C-kännetecken mot dokumenterad variant", expanded=False):
                                        for row in refmatch.get("checklist", []):
                                            marker = "✅" if row.get("observed") is True else "▫️"
                                            st.write(f"{marker} {row.get('label')}: {row.get('expected')}")
                                        st.caption(refmatch.get("reference_image_note", ""))
                                        st.write("**Nästa verifiering:**")
                                        for step in refmatch.get("next_steps", [])[:6]:
                                            st.write("• " + str(step))
                                st.caption(reference_check.get("note", ""))

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

                            checklist_match = match_visual_to_checklist_knowledge(findings, sport=candidate.get("sport") or candidate.get("kategori"))
                            st.markdown(f"**📚 Visuell checklistmatch:** {checklist_match.get('status')}")
                            for cm in checklist_match.get("matches", [])[:3]:
                                icon = "⛔" if cm.get("conflict") else ("✅" if cm.get("match_score", 0) >= 80 else "🧩")
                                st.caption(f"{icon} {cm.get('label')} · strukturmatch {cm.get('match_score', 0):.0f}/100")
                                if cm.get("evidence"):
                                    st.caption("Stöd: " + " • ".join(cm.get("evidence")[:3]))
                                if cm.get("importance_reason"):
                                    st.caption("Varför det spelar roll: " + str(cm.get("importance_reason")))
                                if cm.get("source_url"):
                                    publisher = cm.get("source_publisher") or "officiell källa"
                                    st.markdown(f"[Kontrollera mot {publisher}]({cm.get('source_url')})")
                            st.caption(checklist_match.get("note", ""))

                            exact_identity = resolve_visual_exact_identity(
                                findings,
                                listing_title=candidate.get("titel", ""),
                                listing_raw_text=candidate.get("raw_text", ""),
                                observed_records=get_sold_comp_data(),
                                sport=candidate.get("sport") or candidate.get("kategori"),
                            )
                            st.markdown(f"**🧠 Mest sannolika exakta kort:** {exact_identity.get('status')}")
                            best_card = exact_identity.get("best_candidate")
                            if best_card:
                                icon = "✅" if exact_identity.get("exact_identity_ready") else "🧩"
                                st.caption(
                                    f"{icon} {best_card.get('label')} · kombinerad identitet "
                                    f"{best_card.get('combined_score', 0):.0f}/100"
                                )
                                if best_card.get("reasons"):
                                    st.caption("Varför: " + " • ".join(best_card.get("reasons")[:5]))
                                for caution in best_card.get("cautions", [])[:3]:
                                    st.caption("⚠️ " + caution)
                            if exact_identity.get("alternatives"):
                                st.caption("Alternativ om huvudkandidaten faller:")
                                for alt in exact_identity.get("alternatives", [])[:2]:
                                    st.caption(f"↳ {alt.get('label')} · {alt.get('combined_score', 0):.0f}/100")
                            for action in exact_identity.get("next_actions", [])[:3]:
                                st.caption("🔎 Nästa verifiering: " + action)
                            st.caption(exact_identity.get("note", ""))

                            verified_candidates = [c for c in exact_identity.get("candidates", []) if exact_identity.get("exact_identity_ready") and c is best_card]
                            if verified_candidates:
                                st.success("Identiteten har oberoende stöd. Exact Comp Hunter är upplåst för denna kandidat.")
                                exact_hunt = hunt_exact_comps(verified_candidates[0], get_sold_comp_data())
                                st.markdown(f"**🎯 Exact Comp Hunter:** {exact_hunt.get('status')}")
                                if exact_hunt.get("query"):
                                    st.code(exact_hunt.get("query"), language=None)
                                exact_count = int(exact_hunt.get("exact_sold_count", 0) or 0)
                                near_count = int(exact_hunt.get("near_sold_count", 0) or 0)
                                st.caption(f"Exakta sålda comps i lokal historik: {exact_count} · nära sålda comps: {near_count}")
                                evidence_ladder = build_exact_evidence_ladder(exact_hunt)
                                ladder_counts = {level["key"]: level for level in evidence_ladder.get("levels", [])}
                                st.markdown("**🪜 Comp Evidence Ladder**")
                                st.caption(
                                    f"✅ Exact: {ladder_counts.get('EXACT', {}).get('count', 0)} · "
                                    f"🟡 Near: {ladder_counts.get('NEAR', {}).get('count', 0)} · "
                                    f"👤 Player-only: {ladder_counts.get('PLAYER_ONLY', {}).get('count', 0)} · "
                                    f"⛔ Rejected: {ladder_counts.get('REJECTED', {}).get('count', 0)}"
                                )
                                if evidence_ladder.get("valuation_basis_count", 0):
                                    st.success(f"Värderingsgrund: {evidence_ladder['valuation_basis_count']} verifierade Exact-comps.")
                                else:
                                    st.warning("Värderingsgrund: inga verifierade Exact-comps. Near/Player-only används inte som exakt prisgrund.")
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
                                comp_quality = build_comp_quality_guard(exact_hunt.get("exact") or [])
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
                                spread = comp_quality.get("relative_spread")
                                spread_text = f" · spridning {spread*100:.0f}%" if spread is not None else ""
                                if comp_quality.get("duplicate_observation_count", 0):
                                    st.caption(
                                        f"🔁 {comp_quality.get('raw_exact_count', 0)} Exact-poster → "
                                        f"{comp_quality.get('independent_exact_count', 0)} oberoende försäljningar "
                                        f"efter deduplicering."
                                    )
                                if comp_quality.get("decision_grade"):
                                    st.success(
                                        f"🛡️ Comp Quality Guard: {comp_quality.get('label')} · "
                                        f"{comp_quality.get('recent_count', 0)} färska Exact{spread_text}"
                                    )
                                elif comp_quality.get("status") != "NO_EXACT_COMPS":
                                    st.warning(f"🛡️ Comp Quality Guard: {comp_quality.get('label')}{spread_text}")
                                for blocker in comp_quality.get("blockers", [])[:4]:
                                    st.caption("⛔ " + blocker)
                                for warning in comp_quality.get("warnings", [])[:2]:
                                    st.caption("⚠️ " + warning)

                                scenario_range = build_evidence_scenario_range(
                                    exact_hunt.get("exact") or [],
                                    total_cost=item.get("analysis_total_cost") or item.get("total_cost"),
                                    decision_grade=bool(comp_quality.get("decision_grade")),
                                )
                                if scenario_range.get("available"):
                                    st.markdown("**📐 Evidensbaserat scenariointervall**")
                                    cols = st.columns(3)
                                    for col, scenario in zip(cols, scenario_range.get("scenarios") or []):
                                        with col:
                                            st.metric(scenario.get("label"), f"{scenario.get('resale_price'):.0f} kr")
                                            if scenario.get("net_profit") is not None:
                                                st.caption(f"netto {scenario.get('net_profit'):+.0f} kr · ROI {scenario.get('roi_pct'):+.0f}%")
                                            st.caption(scenario.get("basis"))
                                    st.caption(scenario_range.get("note"))

                                diversity = comp_quality.get("source_diversity") or {}
                                if diversity.get("status") not in (None, "NO_EXACT_COMPS"):
                                    mp = diversity.get("marketplaces") or {}
                                    sellers = diversity.get("sellers") or {}
                                    mp_text = (
                                        f"{mp.get('unique_count', 0)} marknadsplatser"
                                        if mp.get("unique_count", 0) != 1
                                        else f"1 marknadsplats ({mp.get('top_name') or 'okänd'})"
                                    )
                                    seller_text = (
                                        f"{sellers.get('unique_count', 0)} säljare"
                                        if sellers.get("unique_count", 0) != 1
                                        else f"1 säljare ({sellers.get('top_name') or 'okänd'})"
                                    )
                                    st.caption(f"🌐 Comp Source Diversity: {mp_text} · {seller_text}")
                                    for warning in diversity.get("warnings", [])[:2]:
                                        st.caption("↳ ⚠️ " + warning)
                                recency = comp_quality.get("recency_transparency") or {}
                                if recency.get("status") == "DESCRIBED":
                                    st.caption(f"🕒 Comp Recency: nyast {recency.get('newest_age_days')} d · medianålder {recency.get('median_age_days')} d · äldst {recency.get('oldest_age_days')} d")
                                    ages = recency.get("median_carrier_ages_days") or []
                                    if ages: st.caption("↳ Medianpriset formas av comp(s) som är " + " / ".join(f"{int(x)} dagar" for x in ages) + " gamla.")
                                direction = comp_quality.get("market_direction") or {}
                                if direction.get("status") == "DESCRIBED":
                                    arrow = "↗" if direction.get("direction") in ("UP", "MIXED_UP") else ("↘" if direction.get("direction") in ("DOWN", "MIXED_DOWN") else "↔")
                                    st.caption(f"{arrow} Comp Market Direction: {direction.get('label')} · {direction.get('first_price'):.0f} → {direction.get('latest_price'):.0f} kr ({direction.get('pct_change'):+.1f}%)")
                                    st.caption(f"↳ Senaste {direction.get('recent_count')} comps median: {direction.get('recent_median'):.0f} kr · total median {direction.get('overall_median'):.0f} kr")

                                dynamic_bid = build_dynamic_max_bid(
                                    base_max_total=candidate.get("max_total_price"),
                                    shipping=resolve_shipping(candidate)["shipping"],
                                    comp_verdict=comp_verdict,
                                    identity_gate={
                                        "supports_dynamic_max_bid": bool(candidate.get("exact_identity_gate_supports_dynamic_max_bid")),
                                        "blockers": candidate.get("exact_identity_gate_blockers") or [],
                                    },
                                )
                                if dynamic_bid.get("available"):
                                    st.success(
                                        f"🎯 Dynamic Max Bid: {dynamic_bid.get('max_item_price', 0):.0f} kr + "
                                        f"{resolve_shipping(candidate)['shipping']:.0f} kr {'frakt' if resolve_shipping(candidate)['known'] else 'antagen frakt'} "
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

    information_edge_candidates = [x for x in filtered if x.get("is_information_edge_candidate")]
    information_edge_candidates.sort(
        key=lambda x: (x.get("information_edge_score", 0), x.get("market_edge_score", 0)), reverse=True
    )
    if information_edge_candidates:
        with st.expander(f"🔥 Informationsövertag ({len(information_edge_candidates)})", expanded=True):
            st.caption(
                "Dåligt beskrivna eller svårsökta annonser där FlipFynd ser något som bör verifieras före andra köpare. "
                "Detta är INTE ett KÖP-beslut och skapar aldrig ett marknadsvärde."
            )
            for candidate in information_edge_candidates[:10]:
                st.write(
                    f"**{candidate.get('titel', 'Okänd annons')}** · "
                    f"{candidate.get('information_edge_label', 'Informationsedge')} "
                    f"{candidate.get('information_edge_score', 0)}/100"
                )
                if candidate.get("information_edge_reasons"):
                    st.caption(" • ".join(candidate.get("information_edge_reasons")[:3]))
                verify = candidate.get("information_edge_verify_first") or []
                if verify:
                    st.warning("Verifiera först: " + ", ".join(verify[:4]))
                if candidate.get("lank"):
                    st.markdown(f"[Öppna annonsen och verifiera]({candidate.get('lank')})")

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
        valuation_display_safe = bool(item.get("valuation_display_safe", False))
        valuation_display_note = item.get("valuation_display_note") or ""
        sale_probability = item.get("sale_probability", 0) or 0

        with st.container(border=True):
            decision_class = "buy" if raw_decision.startswith("KÖP") else ("watch" if raw_decision == "KANSKE" else "skip")
            decision_text = "STARKT FYND" if raw_decision == "KÖP (starkt fynd)" else ("KÖP" if raw_decision == "KÖP" else ("BEVAKA" if raw_decision == "KANSKE" else "HOPPA ÖVER"))
            score_value = float(item.get("deal_score", 0) or 0)
            quick_price_label = "AKTUELLT" if sale_type == "Auktion" else "KÖP FÖR"
            quick_market_value = (
                f"{expected:.0f} kr"
                if valuation_display_safe and expected > 0 else "Otillräckligt underlag"
            )
            quick_profit = f"{net_profit:.0f} kr" if valuation_display_safe else "Ej beräknad"
            shipping_raw = item.get("frakt")
            shipping_known = isinstance(shipping_raw, (int, float)) and shipping_raw >= 0
            shipping_info = resolve_shipping(item)
            shipping_used = shipping_info["shipping"]
            shipping_display = f"{shipping_used:.0f} kr" if shipping_known else f"{shipping_used:.0f} kr*"
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
                      <div class="ff-quick-cell"><div class="ff-quick-label">FRAKT</div><div class="ff-quick-value">{shipping_display}</div></div>
                      <div class="ff-quick-cell"><div class="ff-quick-label">UPPSKATTAT MARKNADSVÄRDE</div><div class="ff-quick-value">{quick_market_value}</div></div>
                      <div class="ff-quick-cell"><div class="ff-quick-label">MÖJLIG NETTOVINST</div><div class="ff-quick-value">{quick_profit}</div></div>
                      <div class="ff-quick-cell"><div class="ff-quick-label">SÄLJBARHET</div><div class="ff-quick-value">{item.get('liquidity_label', 'Ej bedömd')}</div></div>
                    </div>
                    <div class="ff-retro-rule"></div>
                  </div>"""
            st.markdown(result_html, unsafe_allow_html=True)
            capital = item.get("capital_efficiency") or {}
            if capital.get("score") is not None:
                downside_text = (
                    f"{float(capital.get('downside') or 0):.0f} kr"
                    if float(capital.get("downside") or 0) < 0 else "ingen beräknad förlust"
                )
                st.caption(
                    f"💸 Kapital: {capital.get('label')} · "
                    f"{float(capital.get('profit_30d') or 0):.0f} kr vinst/30 dagar · "
                    f"{float(capital.get('roi_30d_pct') or 0):.0f}%/30 dagar · "
                    f"nedsida: {downside_text}"
                )

            if item.get("visual_image_urls"):
                image_urls = item.get("visual_image_urls")[:3]
                img_col, info_col = st.columns([1, 3])
                with img_col:
                    st.image(image_urls[0], use_container_width=True)
                with info_col:
                    st.caption("Kortbild – liten förhandsvisning. Öppna bildgalleriet om du vill granska detaljer.")
                    if len(image_urls) > 1:
                        with st.expander(f"🖼️ Visa fler bilder ({len(image_urls)})", expanded=False):
                            gallery_cols = st.columns(len(image_urls))
                            for gallery_col, img_url in zip(gallery_cols, image_urls):
                                with gallery_col:
                                    st.image(img_url, use_container_width=True)
            if item.get("visual_verification_required"):
                st.info(
                    f"👁️ {item.get('visual_edge_label', 'Bildkontroll')} · "
                    f"{float(item.get('visual_edge_score', 0)):.0f}/100 — "
                    + " • ".join(item.get("visual_edge_reasons", [])[:2])
                )
                st.caption("Visual Edge är en granskningssignal. Bildinnehållet är ännu inte automatiskt verifierat av modellen.")

            if not shipping_known:
                st.caption("⚠️ Frakten kunde inte läsas säkert. 29 kr används som kalkylantagande tills annonsen verifierats.")
            elif sale_type == "Auktion" and auction_buffer:
                st.caption(
                    f"Auktionskalkylen använder {analysis_total_cost:.0f} kr inklusive {auction_buffer:.0f} kr försiktig budbuffert."
                )

            why_reasons = []
            if item.get("comp_valuation_basis") == "sold":
                why_reasons.append("verifierade sålda jämförelser används")
            elif item.get("comp_valuation_basis") == "active":
                why_reasons.append("värderingen bygger främst på aktiva annonser – lägre säkerhet")
            if valuation_display_safe and net_profit > 0:
                why_reasons.append(f"kalkylen visar cirka {net_profit:.0f} kr nettovinst")
            liquidity_label = item.get("liquidity_label")
            if liquidity_label:
                why_reasons.append(f"säljbarhet: {liquidity_label}")
            confidence_level = item.get("deal_confidence_level")
            if confidence_level:
                why_reasons.append(f"fyndsäkerhet: {confidence_level}")
            if why_reasons:
                st.markdown("**Varför?** " + " · ".join(why_reasons[:3]))

            max_total_price = item.get("max_total_price")
            max_item_price = item.get("max_item_price")
            max_shipping = resolve_shipping(item)
            if max_total_price is not None and max_item_price is not None:
                if sale_type == "Auktion":
                    st.success(
                        f"🎯 Max bud: {max_item_price:.0f} kr"
                        f" + {max_shipping['shipping']:.0f} kr {'frakt' if max_shipping['known'] else 'antagen frakt'}"
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

            edge_reasons = []
            verify = item.get("information_edge_verify_first") or []
            if item.get("is_information_edge_candidate"):
                edge_reasons.append(item.get("information_edge_label", "Viktig variantinfo kan vara underskattad"))
            if item.get("is_market_edge_candidate"):
                market_reasons = item.get("market_edge_reasons") or []
                edge_reasons.extend(market_reasons[:1] or [item.get("market_edge_label", "Marknadsedge")])
            if item.get("is_hidden_find_candidate"):
                edge_reasons.append("Annonsen kan vara svårare för andra köpare att hitta")
            if item.get("misclassified_card_candidate"):
                edge_reasons.append("Annonsen kan vara felklassificerad eller ofullständigt beskriven")
            if item.get("mispriced_rookie_candidate"):
                edge_reasons.append("Rookie-signal som behöver verifieras")
            if edge_reasons:
                unique_edge_reasons = list(dict.fromkeys(str(x) for x in edge_reasons if x))
                st.info("🔥 **Informationsövertag** — " + " • ".join(unique_edge_reasons[:3]))
                if verify:
                    st.caption("Verifiera först: " + ", ".join(verify[:4]))
                st.caption("Researchsignal – ändrar inte KÖP-beslut utan verifierad identitet och tillräckligt prisunderlag.")

            # Detailed liquidity, confidence, velocity, risk and identity diagnostics live in
            # “Visa full analys”. The decision card intentionally stays action-first.

            render_card_explanation_button(item, f"result_{index}")

            journal_key = f"journal_add_{index}_{hashlib.sha1(str(item.get('lank') or item.get('titel')).encode('utf-8')).hexdigest()[:8]}"
            if st.button("📒 Logga som köpt", key=journal_key, use_container_width=True):
                journal_rows = _load_flip_journal_records()
                if any(r.get("listing_url") and r.get("listing_url") == item.get("lank") for r in journal_rows):
                    st.info("Den här annonsen finns redan i Flip Journal.")
                else:
                    purchase_price = float(item.get("pris") or 0) + (float(item.get("frakt")) if isinstance(item.get("frakt"), (int, float)) else 29.0)
                    journal_rows.append(build_entry_from_listing(item, purchase_price=purchase_price))
                    _save_flip_journal_records(journal_rows)
                    st.success("Köpet är loggat i Flip Journal. Kontrollera det faktiska inköpspriset i journalen om det avviker.")

            # Keep technical scoring out of the primary decision flow. It remains available
            # below for users who explicitly open the full analysis.

            if item.get("decision_confidence_audit_downgraded"):
                blockers = item.get("decision_confidence_audit_blockers") or []
                reason = blockers[0] if blockers else "beslutsunderlaget är för tunt"
                st.warning(f"🛡️ KÖP stoppades av beslutsgranskningen: {reason}.")
            if item.get("decision_conflict_audit_downgraded"):
                st.warning(
                    "⚖️ KÖP stoppades eftersom analysens signaler motsäger varandra: "
                    + str(item.get("decision_conflict_audit_summary") or "verifiera caset innan köp")
                )

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

            with st.expander("🔎 Visa hela analysen och underlaget"):
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
                    with st.expander("🛡️ Decision Confidence Audit", expanded=False):
                        st.markdown(
                            f"**{item.get('decision_confidence_audit_label', 'Ej bedömd')}** · "
                            f"{int(item.get('decision_confidence_audit_score', 0) or 0)}/100"
                        )
                        if item.get("decision_confidence_audit_downgraded"):
                            st.warning(
                                f"Ursprungligt beslut {item.get('decision_pre_confidence_audit', 'KÖP')} "
                                "sänktes till KANSKE eftersom bevisunderlaget var för tunt."
                            )
                        for blocker in (item.get("decision_confidence_audit_blockers") or [])[:5]:
                            st.caption("⛔ " + str(blocker))
                        for warning in (item.get("decision_confidence_audit_warnings") or [])[:4]:
                            st.caption("⚠️ " + str(warning))
                        for strength in (item.get("decision_confidence_audit_strengths") or [])[:4]:
                            st.caption("✅ " + str(strength))
                        st.caption(
                            item.get("decision_confidence_audit_note")
                            or "Granskningen kan bara sänka ett KÖP, aldrig skapa ett köpbeslut."
                        )
                    with st.expander("⚖️ Decision Conflict Audit", expanded=False):
                        st.markdown(
                            f"**{item.get('decision_conflict_audit_label', 'Ej bedömd')}**"
                        )
                        st.caption(
                            item.get("decision_conflict_audit_summary")
                            or "Kontrollerar om fyndsignal, risk, säljbarhet, nedsida och evidens säger emot varandra."
                        )
                        if item.get("decision_conflict_audit_downgraded"):
                            st.warning(
                                f"Beslutet {item.get('decision_pre_conflict_audit', 'KÖP')} sänktes till KANSKE "
                                "eftersom motsägelserna blev för stora."
                            )
                        for conflict in (item.get("decision_conflict_audit_conflicts") or [])[:6]:
                            severity = str((conflict or {}).get("severity") or "moderate")
                            prefix = "⛔" if severity == "hard" else "⚠️"
                            st.caption(prefix + " " + str((conflict or {}).get("message") or "Motsägelse i analysen"))
                        for strength in (item.get("decision_conflict_audit_strengths") or [])[:4]:
                            st.caption("✅ " + str(strength))
                        st.caption(
                            item.get("decision_conflict_audit_note")
                            or "Granskningen kan aldrig skapa eller uppgradera ett köpbeslut."
                        )
                    st.write(
                        f"**Risk:** {item.get('risk_label', 'Okänd')} "
                        f"({item.get('risk_score', 0)}/100)"
                    )
                    if item.get("card_identity"):
                        st.write(f"**Kortidentitet:** {item.get('card_identity')}")
                    with st.expander("🔐 Exact Identity Gate", expanded=False):
                        st.markdown(f"**{item.get('exact_identity_gate_label', 'Exakt identitet låst')}** · {int(item.get('exact_identity_gate_score', 0) or 0)}/100")
                        if item.get("exact_identity_gate_supports_exact_comp_search"):
                            st.success("Exakt comp-sökning får användas för detta kort.")
                        else:
                            st.warning("Exakt comp-sökning är låst tills identiteten är tillräckligt komplett.")
                        if item.get("exact_identity_gate_supports_dynamic_max_bid"):
                            st.success("Identiteten är även stark nog för ett comp-stött dynamiskt maxbud, om comp-underlaget också godkänns.")
                        else:
                            st.caption("Dynamiskt maxbud är låst av identitetsgrinden.")
                        for blocker in (item.get("exact_identity_gate_blockers") or [])[:5]:
                            st.caption("⛔ " + str(blocker))
                        for warning in (item.get("exact_identity_gate_warnings") or [])[:4]:
                            st.caption("⚠️ " + str(warning))
                        reqs = item.get("exact_identity_gate_requirements") or []
                        if reqs:
                            st.markdown("**Exakta comps måste uppfylla:**")
                            for req in reqs[:8]:
                                st.caption("• " + str(req))
                        st.caption(item.get("exact_identity_gate_note") or "")

                    if item.get("premium_comp_hunter_active"):
                        with st.expander("💎 Premium Comp Hunter", expanded=False):
                            exact_count = int(item.get("premium_comp_hunter_exact_count", 0) or 0)
                            near_count = int(item.get("premium_comp_hunter_near_count", 0) or 0)
                            st.markdown(f"**{item.get('premium_comp_hunter_status', 'Premium comps granskas')}**")
                            cpc1, cpc2 = st.columns(2)
                            with cpc1:
                                st.metric("Exakta premium-sålda", exact_count)
                            with cpc2:
                                st.metric("Närliggande premium-sålda", near_count)
                            premium_ladder = build_premium_evidence_ladder({
                                "active": item.get("premium_comp_hunter_active"),
                                "exact": item.get("premium_comp_hunter_exact") or [],
                                "near": item.get("premium_comp_hunter_near") or [],
                                "rejected": item.get("premium_comp_hunter_rejected") or [],
                                "insufficient_count": item.get("premium_comp_hunter_insufficient_count", 0),
                                "safe_for_valuation": item.get("premium_comp_hunter_safe_for_valuation"),
                            })
                            premium_levels = {level["key"]: level for level in premium_ladder.get("levels", [])}
                            premium_quality = build_comp_quality_guard(item.get("premium_comp_hunter_exact") or [])
                            st.caption(
                                "🪜 Evidence: "
                                f"Exact premium {premium_levels.get('EXACT_PREMIUM', {}).get('count', 0)} · "
                                f"Near {premium_levels.get('NEAR_PREMIUM', {}).get('count', 0)} · "
                                f"Otillräckliga {premium_levels.get('INSUFFICIENT', {}).get('count', 0)} · "
                                f"Rejected {premium_levels.get('REJECTED', {}).get('count', 0)}"
                            )
                            st.caption("Endast verifierade Exact premium-comps får bära premiumvärderingen.")
                            if premium_quality.get("duplicate_observation_count", 0):
                                st.caption(
                                    f"🔁 {premium_quality.get('raw_exact_count', 0)} Exact premium-poster → "
                                    f"{premium_quality.get('independent_exact_count', 0)} oberoende försäljningar."
                                )
                            premium_diversity = premium_quality.get("source_diversity") or {}
                            if premium_diversity.get("status") not in (None, "NO_EXACT_COMPS"):
                                mp = premium_diversity.get("marketplaces") or {}
                                sellers = premium_diversity.get("sellers") or {}
                                st.caption(
                                    f"🌐 Premium Source Diversity: {mp.get('unique_count', 0)} marknadsplatser · "
                                    f"{sellers.get('unique_count', 0)} säljare"
                                )
                                for warning in premium_diversity.get("warnings", [])[:2]:
                                    st.caption("↳ ⚠️ " + warning)
                            premium_recency = premium_quality.get("recency_transparency") or {}
                            if premium_recency.get("status") == "DESCRIBED":
                                st.caption(f"🕒 Premium Recency: nyast {premium_recency.get('newest_age_days')} d · medianålder {premium_recency.get('median_age_days')} d · äldst {premium_recency.get('oldest_age_days')} d")
                            premium_direction = premium_quality.get("market_direction") or {}
                            if premium_direction.get("status") == "DESCRIBED":
                                arrow = "↗" if premium_direction.get("direction") in ("UP", "MIXED_UP") else ("↘" if premium_direction.get("direction") in ("DOWN", "MIXED_DOWN") else "↔")
                                st.caption(f"{arrow} Premium Market Direction: {premium_direction.get('label')} · {premium_direction.get('first_price'):.0f} → {premium_direction.get('latest_price'):.0f} kr ({premium_direction.get('pct_change'):+.1f}%)")
                            premium_direction_evidence = premium_quality.get("market_direction_evidence") or {}
                            if premium_direction_evidence.get("status") == "DESCRIBED":
                                st.caption(f"🔎 Premium riktningsunderlag: {premium_direction_evidence.get('exact_count')} comps · {premium_direction_evidence.get('span_days')} dagar")
                            if premium_quality.get("decision_grade"):
                                st.success("🛡️ Premium Comp Quality: beslutsstarkt även avseende antal, färskhet och prisspridning.")
                            elif exact_count:
                                st.warning(f"🛡️ Premium Comp Quality: {premium_quality.get('label')} – exakt identitet räcker inte ensam.")
                                for blocker in premium_quality.get("blockers", [])[:3]:
                                    st.caption("⛔ " + blocker)
                            if item.get("premium_comp_hunter_safe_for_valuation"):
                                st.success("Premiumkortet har tillräckligt med exakta sålda jämförelser för att prisunderlaget ska få användas vidare.")
                            else:
                                st.warning("Breda samma-spelare-comps räcker inte. Minst två exakta premiumförsäljningar behövs för realistiskt värde.")
                            query = item.get("premium_comp_hunter_query")
                            if query:
                                st.caption(f"Exakt sökfras: {query}")
                            for comp in (item.get("premium_comp_hunter_exact") or [])[:4]:
                                price = comp.get("price")
                                price_text = f" · {float(price):.0f} kr" if isinstance(price, (int, float)) else ""
                                st.caption(f"✅ {comp.get('title', 'Såld comp')}{price_text}")
                            for comp in (item.get("premium_comp_hunter_near") or [])[:3]:
                                missing = ", ".join(comp.get("missing") or [])
                                st.caption(f"🟡 {comp.get('title', 'Närliggande comp')}" + (f" · saknar: {missing}" if missing else ""))
                            targets = item.get("premium_comp_hunter_search_targets") or []
                            if targets:
                                st.markdown("**Sök efter exakt samma premiumkort:**")
                                cols = st.columns(min(2, len(targets)))
                                for idx, target in enumerate(targets[:2]):
                                    with cols[idx]:
                                        st.link_button(str(target.get("platform") or "Sök"), str(target.get("url") or "#"), use_container_width=True)
                            if item.get("premium_valuation_safe_for_display"):
                                st.markdown("**Exakt premiumintervall**")
                                pv1, pv2, pv3 = st.columns(3)
                                with pv1:
                                    st.metric("Observerat låg", f"{float(item.get('premium_valuation_low') or 0):.0f} kr")
                                with pv2:
                                    st.metric("Färskhetsvägt basvärde", f"{float(item.get('premium_valuation_base') or 0):.0f} kr")
                                with pv3:
                                    st.metric("Observerat hög", f"{float(item.get('premium_valuation_high') or 0):.0f} kr")
                                spread = item.get("premium_valuation_spread_pct")
                                fresh = int(item.get("premium_valuation_fresh_count", 0) or 0)
                                conf = item.get("premium_valuation_confidence") or "låg"
                                spread_text = f"{float(spread):.0f}%" if isinstance(spread, (int, float)) else "ej beräknad"
                                st.caption(f"Spridning: {spread_text} · färska avslut ≤180 dagar: {fresh} · intervallsäkerhet: {conf}")
                                st.caption(item.get("premium_valuation_note") or "")
                            st.caption(item.get("premium_comp_hunter_note") or "")

                with d2:
                    if valuation_display_safe:
                        st.write(f"**Försiktigt värde:** {floor:.0f} kr")
                        st.write(f"**Förväntat värde:** {expected:.0f} kr")
                        st.write(f"**Best case:** {best_case:.0f} kr")
                        st.write(f"**Riskjusterad vinst:** {item.get('risk_adjusted_profit', 0)} kr")
                        st.write(f"**ROI:** {item.get('roi_estimate', 0)}")
                    else:
                        st.write("**Prisvärdering:** Otillräckligt underlag")
                        st.write("**Riskjusterad vinst:** Ej beräknad")
                        st.write("**ROI:** Ej beräknad")
                        st.caption(valuation_display_note)
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
                        rarity_entries = item.get("rarity_evidence_entries") or []
                        if rarity_entries:
                            st.write(f"**Raritetsbevis:** {item.get('rarity_evidence_status') or 'Ej klassificerat'}")
                            for rarity_row in rarity_entries[:4]:
                                label = rarity_row.get("label") or "Känd struktur"
                                status = rarity_row.get("status") or ""
                                st.write(f"• {label}: {status}")
                            for rarity_warning in (item.get("rarity_evidence_warnings") or [])[:3]:
                                st.warning(rarity_warning)
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
    st.caption("Uppdatera annonser med knappen högst upp. Här finns lagring och felsökning.")

    with st.expander("💾 Persistent lagring", expanded=False):
        persistence = storage_status(DATABASE_URL)
        if not persistence.configured:
            st.warning("Ingen persistent databas är aktiverad i Streamlit ännu. Flip Journal och verifierade sold comps använder därför lokal runtime-lagring.")
            st.caption("Lägg in FLIPFYND_DATABASE_URL i Streamlit Secrets. Databasadressen ska aldrig sparas i GitHub-koden.")
        else:
            health = _cached_storage_probe(DATABASE_URL)
            if health.durable:
                st.success("✅ Persistent databas: ansluten och verifierad")
                st.caption("Flip Journal och verifierade sold comps använder PostgreSQL. Anslutningen kontrolleras med en lätt read-only hälsokontroll och cachas i 60 sekunder.")
                try:
                    ns_rows = namespace_status(DATABASE_URL)
                    known = {row.get("namespace") for row in ns_rows}
                    journal_ok = "flip_journal" in known
                    comps_ok = "sold_comps" in known
                    st.caption(f"Dataytor: Flip Journal {'✓' if journal_ok else '–'} · Sold comps {'✓' if comps_ok else '–'}")
                except Exception as exc:
                    _record_storage_error("status", exc)
                    st.warning("Databasen svarar, men metadata för lagringsytorna kunde inte läsas just nu.")
            else:
                st.error("Databasadressen finns, men anslutningen kunde inte verifieras. FlipFynd använder lokal fallback tills databasen fungerar igen.")
                st.caption(health.detail)

        pending = pending_summary(PENDING_SYNC_PATH)
        if pending["count"]:
            labels = {"flip_journal": "Flip Journal", "sold_comps": "Sold comps"}
            pending_names = ", ".join(labels.get(name, name) for name in pending["namespaces"] if name)
            st.error(f"⚠️ Osynkroniserade lokala ändringar: {pending["count"]} datayta(or) · {pending_names}")
            st.caption("FlipFynd visar den lokala väntande versionen tills den har skrivits till databasen. Ingen automatisk sammanslagning görs, så en nyare lokal ändring kan inte tyst ersättas av en äldre databasversion.")
            if DATABASE_URL and st.button("↻ Försök synka väntande data", use_container_width=True, key="retry_pending_storage_sync"):
                sync_result = _retry_pending_sync()
                if sync_result["remaining"] == 0:
                    st.success("Alla väntande ändringar har synkats till den persistenta databasen.")
                else:
                    st.warning(f"{sync_result['remaining']} datayta(or) väntar fortfarande på synkning.")
                st.rerun()
        elif DATABASE_URL:
            st.caption("Synkstatus: inga väntande lokala ändringar.")

        storage_errors = [
            st.session_state.get("storage_error_flip_journal"),
            st.session_state.get("storage_error_sold_comps"),
            st.session_state.get("storage_error_status"),
        ]
        if any(storage_errors):
            st.error("Persistent lagring har rapporterat ett fel vid en tidigare operation. FlipFynd fortsätter med lokal fallback när det behövs i stället för att stoppa appen.")

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
                    existing = _load_sold_comp_records()
                    result = acquire_sold_batch(
                        rows,
                        existing=existing,
                        source_key=f"manual_upload:{sold_upload.name}",
                    )
                    if result["added_count"]:
                        _save_sold_comp_records(result["records"])
                        get_sold_comp_data.clear()
                        clear_analysis_cache()
                        st.session_state["result_cache"] = {}
                    st.success(
                        f"{result['added_count']} nya comps importerade • "
                        f"{result['duplicate_count']} dubbletter • {result['quarantine_count']} i karantän."
                    )
                    if result["quarantine"]:
                        with st.expander("Visa karantän"):
                            for err in result["quarantine"][:25]:
                                st.write(f"Rad {err['row']}: {err['reason']}")
                    st.caption(f"Pipeline: {result['exact_ready_count']} exakt klara • {result['review_count']} behöver identitetsgranskning. Batch {result['batch_id']}")
                except Exception as exc:
                    st.error(f"Importen kunde inte läsas: {exc}")

    with st.expander("Sold Source Readiness"):
        readiness = source_readiness_summary()
        st.caption(
            "FlipFynd skiljer på en webbplats som är bra för manuell comp-research och en källa som faktiskt kan "
            "integreras stabilt och verifierbart. Research-only får aldrig marknadsföras som automatisk sold-data."
        )
        r1, r2, r3 = st.columns(3)
        r1.metric("Kända källor", readiness["source_count"])
        r2.metric("Automatiskt anslutna", readiness["automated_count"])
        r3.metric("Research-only", readiness["research_only_count"])
        if readiness["automated_count"] == 0:
            st.warning(
                "Ingen extern sold-källa är ännu automatiskt ansluten. Det är en verklig begränsning: "
                "FlipFynd ska hellre visa detta än låtsas ha live-comps."
            )
        for source in sold_source_registry():
            cols = st.columns([2, 2, 5])
            cols[0].markdown(f"**{source['label']}**")
            cols[1].write(source["status"])
            cols[2].caption(source["note"])
            cols[2].markdown(f"[Öppna för comp-research ↗]({source['research_url']})")

    with st.expander("External Sold Source Adapter"):
        st.caption(
            "Källadaptrar översätter externa exporter till FlipFynds strikta sold-comp-format. "
            "De hämtar inget från internet själva och en avslutad annons räknas aldrig som såld utan explicit såld-evidens."
        )
        adapter_options = {item["label"]: item["key"] for item in available_adapters()}
        adapter_label = st.selectbox("Källformat", list(adapter_options), key="external_sold_adapter")
        external_upload = st.file_uploader(
            "Välj extern CSV eller JSON", type=["csv", "json"], key="external_sold_upload"
        )
        if external_upload is not None and st.button("Validera extern sold-data", use_container_width=True):
            try:
                rows = parse_import_bytes(external_upload.getvalue(), external_upload.name)
                existing = _load_sold_comp_records()
                result = import_external_sold_rows(
                    rows, adapter_options[adapter_label], existing=existing
                )
                if result["added_count"]:
                    _save_sold_comp_records(result["records"])
                    get_sold_comp_data.clear()
                    clear_analysis_cache()
                    st.session_state["result_cache"] = {}
                st.success(
                    f"{result['added_count']} nya verifierade comps • "
                    f"{result['duplicate_count']} dubbletter • "
                    f"{result['adapter_rejected_count']} saknade explicit såld-evidens • "
                    f"{result['error_count']} avvisades av säkerhetsgrinden."
                )
                if result["adapter_rejections"] or result["errors"]:
                    with st.expander("Visa varför rader avvisades"):
                        for err in result["adapter_rejections"][:25]:
                            st.write(f"Rad {err['row']}: {err['reason']}")
                        for err in result["errors"][:25]:
                            st.write(f"Rad {err['row']}: {err['error']}")
            except Exception as exc:
                st.error(f"Extern sold-data kunde inte valideras: {exc}")

    with st.expander("Smart Sold Comp Acquisition"):
        st.caption(
            "FlipFynd söker bara i kända lokala datakällor och tar enbart in rader med direkt såld-evidens. "
            "Ended/closed räcker aldrig. Aktiva priser får aldrig bli sold comps av misstag."
        )
        current_sold = _load_sold_comp_records()
        sold_audit = audit_sold_comp_records(current_sold)
        st.write(f"**{sold_audit['safe_count']} verifierade sold comps godkända för värdering i denna datamiljö.**")
        if sold_audit["blocked_count"]:
            st.warning(
                f"{sold_audit['blocked_count']} äldre eller ofullständigt verifierade sold-rader är blockerade från värderingen. "
                "De raderas inte automatiskt; FlipFynd använder dem bara inte som realiserade prisbevis."
            )
        aq1, aq2, aq3 = st.columns(3)
        aq1.metric("Godkända", sold_audit["safe_count"])
        aq2.metric("Stark metadata", sold_audit["strong_count"])
        aq3.metric("Blockerade", sold_audit["blocked_count"])
        if sold_audit["blocked_count"]:
            with st.expander("Visa Sold Comp Data Quality Audit"):
                labels = {
                    "missing_verified_status": "saknar verifieringsstatus",
                    "missing_explicit_sale_evidence_metadata": "saknar explicit försäljningsevidens",
                    "missing_positive_realised_price": "saknar positivt realiserat pris",
                    "not_an_object": "ogiltigt radformat",
                }
                for reason, count in sorted(sold_audit["rejection_reasons"].items(), key=lambda x: (-x[1], x[0])):
                    st.write(f"- {count}: {labels.get(reason, reason)}")
                st.caption(
                    "Audit-grinden ändrar inte eller raderar historik. Den hindrar bara osäkra sold-rader från att bära värdering. "
                    "En rad måste ha både verifieringsstatus, explicit försäljningsevidens och ett positivt realiserat pris."
                )
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Sök verifierade avslut", type="primary", use_container_width=True):
                if smart_collect_local_sold_comps is None:
                    st.error(
                        "Smart Sold Comp Acquisition är tillfälligt avstängd eftersom deployen innehåller en äldre "
                        "sold_comp_collector. Resten av FlipFynd kan användas. Synka hela releasen för att återaktivera funktionen."
                    )
                else:
                    try:
                        result = smart_collect_local_sold_comps(
                            BASE_DIR,
                            existing=current_sold,
                            exclude=[SOLD_COMPS_PATH],
                        )
                        if result["added_count"]:
                            _save_sold_comp_records(result["records"])
                            get_sold_comp_data.clear()
                            clear_analysis_cache()
                            st.session_state["result_cache"] = {}
                        st.success(
                            f"{result['added_count']} nya verifierade avslut • "
                            f"{result['sources_scanned']} källor skannade • "
                            f"{result['duplicate_count']} dubbletter • "
                            f"{result['not_sold_count']} utan tillräcklig såld-evidens • "
                            f"{result['invalid_count']} ogiltiga."
                        )
                        with st.expander("Visa källdiagnostik"):
                            if not result["source_reports"]:
                                st.info("Inga kända lokala källfiler hittades utöver sold-comp-biblioteket.")
                            for report in result["source_reports"]:
                                source_name = Path(report["source"]).name
                                if report.get("error"):
                                    st.write(f"**{source_name}:** kunde inte läsas — {report['error']}")
                                    continue
                                st.write(
                                    f"**{source_name}:** {report['rows']} rader • "
                                    f"{report['candidate_count']} verifierbara • "
                                    f"{report['added_count']} nya • {report['duplicate_count']} dubbletter"
                                )
                            if result.get("rejection_reasons"):
                                st.caption("Avvisningsorsaker")
                                labels = {
                                    "price_without_sold_evidence": "pris finns men ingen såld-evidens",
                                    "missing_sold_evidence": "såld-evidens saknas",
                                    "sold_state_without_price": "såld-status finns men pris saknas",
                                    "non_positive_sold_price": "sold_price är inte positivt",
                                    "invalid_normalized_row": "raden kunde inte valideras",
                                    "not_an_object": "ogiltigt radformat",
                                }
                                for reason, count in sorted(result["rejection_reasons"].items(), key=lambda x: (-x[1], x[0])):
                                    st.write(f"- {count}: {labels.get(reason, reason)}")
                    except Exception as exc:
                        st.error(f"Smart collector kunde inte köras: {exc}")
        with c2:
            if st.button("Samla från inlästa annonser", use_container_width=True):
                try:
                    source_rows = get_data()
                    result = collect_sold_comps(
                        source_rows,
                        existing=current_sold,
                        source_name="tradera_loaded_data",
                    )
                    if result["added_count"]:
                        _save_sold_comp_records(result["records"])
                        get_sold_comp_data.clear()
                        clear_analysis_cache()
                        st.session_state["result_cache"] = {}
                    st.success(
                        f"{result['added_count']} nya verifierade avslut • "
                        f"{result['duplicate_count']} dubbletter • "
                        f"{result['not_sold_count']} ignorerade • {result['invalid_count']} ogiltiga."
                    )
                except Exception as exc:
                    st.error(f"Collector kunde inte köras: {exc}")
        with c3:
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
            "VERIFIED SOLD betyder att källraden har ett explicit sålt pris eller explicit såld-status tillsammans med pris. "
            "Det betyder inte att FlipFynd har verifierat kortets exakta identitet; den kontrollen görs separat innan en comp får bära värderingen."
        )
        intake = sold_comp_intake_audit(current_sold)
        with st.expander("Exact Comp Intake – vad kan faktiskt användas exakt?"):
            st.caption(
                "En riktig försäljning är inte automatiskt en exakt comp. Här separeras försäljningsbevis från kortidentitet."
            )
            iq1, iq2, iq3, iq4 = st.columns(4)
            iq1.metric("Exakt klara", intake["exact_ready_count"])
            iq2.metric("Behöver ID-koll", intake["identity_review_count"])
            iq3.metric("Bara såld-bevis", intake["sale_only_count"])
            iq4.metric("Avvisade", intake["rejected_count"])
            review_rows = [r for r in intake["records"] if r["status"] != "EXACT_READY"]
            if review_rows:
                st.write("**Prioriterad granskningskö**")
                for row in review_rows[:20]:
                    missing = ", ".join(row.get("missing_identity_fields") or [])
                    reason = "; ".join(row.get("blockers") or [])
                    suffix = f" · saknas: {missing}" if missing else ""
                    st.write(f"- {row['title'] or 'Namnlös rad'} — {row['status']}{suffix} · {reason}")
            else:
                st.success("Alla verifierade sold-rader i biblioteket har även komplett, uttryckligen bekräftad exakt identitet.")
            st.caption(
                "Exakt klar betyder inte att raden matchar varje analyserat kort. Den får bara gå vidare till den separata matchningen mot spelare, set, år, kortnummer och relevant variant/gradering."
            )

        with st.expander("🎯 Sold Data Expansion – vad saknas för korten jag faktiskt hittar?", expanded=False):
            current_candidates = st.session_state.get("results") or []
            queue = build_sold_research_queue(current_candidates, current_sold, limit=12)
            st.caption(
                "FlipFynd prioriterar sold-research utifrån dina redan analyserade kandidater. "
                "Kön använder bara strukturerad kortidentitet och verifierade exact-ready avslut."
            )
            if not current_candidates:
                st.info("Kör först en fyndanalys. Då kan FlipFynd visa vilka sold-data som saknas för just de korten.")
            else:
                q1, q2, q3, q4 = st.columns(4)
                q1.metric("Saknar exakt sold", queue["no_exact_sold_count"])
                q2.metric("Bara 1 exakt sold", queue["thin_exact_sold_count"])
                q3.metric("Verifiera ID först", queue["identity_first_count"])
                q4.metric("Har ≥2 exakta sold", queue["has_exact_sold_count"])

                labels = {
                    "NO_EXACT_SOLD": "SAKNAR EXAKT SOLD",
                    "THIN_EXACT_SOLD": "TUNT SOLD-UNDERLAG",
                    "IDENTITY_FIRST": "VERIFIERA IDENTITET FÖRST",
                    "HAS_EXACT_SOLD": "SOLD-UNDERLAG FINNS",
                }
                for idx, row in enumerate(queue.get("rows") or [], start=1):
                    with st.container(border=True):
                        st.markdown(f"**#{idx} {row['title']}**")
                        st.write(f"**{labels.get(row['status'], row['status'])}** · {row['action']}")
                        identity = row.get("identity") or {}
                        identity_parts = []
                        if identity.get("player_name"):
                            identity_parts.append(str(identity["player_name"]))
                        if identity.get("set_name"):
                            identity_parts.append(str(identity["set_name"]))
                        if identity.get("season"):
                            identity_parts.append(str(identity["season"]))
                        if identity.get("card_number"):
                            identity_parts.append(f"#{identity['card_number']}")
                        if identity_parts:
                            st.caption(" · ".join(identity_parts))
                        if row.get("missing_identity_fields"):
                            st.caption("Saknas för exakt matchning: " + ", ".join(row["missing_identity_fields"]))
                        else:
                            st.caption(f"Verifierade exakta sold comps i biblioteket: {row['exact_sold_count']}")
                        if row.get("url"):
                            st.link_button("Öppna annonsen ↗", row["url"], use_container_width=True)
                st.caption(queue["note"])

            eligible_research = [
                row for row in (queue.get("rows") or [])
                if row.get("status") in {"NO_EXACT_SOLD", "THIN_EXACT_SOLD", "HAS_EXACT_SOLD"}
                and not row.get("missing_identity_fields")
            ]
            if eligible_research:
                st.markdown("#### 🔎 Research-assistent")
                research_labels = {
                    f"{idx+1}. {row['title']} · {row['exact_sold_count']} exakt sold": idx
                    for idx, row in enumerate(eligible_research)
                }
                selected_label = st.selectbox(
                    "Välj kandidatkort",
                    list(research_labels),
                    key="sold_research_candidate",
                    help="Sökfrasen byggs bara av strukturerad identitet, aldrig genom gissning från annonsrubriken.",
                )
                research_row = eligible_research[research_labels[selected_label]]
                research_identity = research_row.get("identity") or {}
                research_query = build_exact_research_query(research_identity)

                if research_query.get("ready"):
                    progress = research_progress(research_row.get("exact_sold_count"), target=2)
                    st.progress(min(1.0, progress["exact_sold_count"] / progress["target"]))
                    st.caption(progress["label"] + " · " + progress["note"])
                    st.caption("Exakt sökfras")
                    st.code(research_query["query"], language=None)
                    comp_plan = build_comp_research_plan(research_identity)
                    with st.expander("Vilken comp-källa ska jag lita mest på?", expanded=False):
                        st.write("**Prioritet:** Tradera verifierade avslut + eBay Product Research/eBay Sold först; därefter Card Ladder, Fanatics Collect och COMC. 130 Point och SportsCardsPro används främst som kontroll/context beroende på om en individuell sale kan verifieras.")
                        st.caption(comp_plan["rule"])
                        for source_row in comp_plan["sources"]:
                            st.write(f"**{source_row['priority']}. {source_row['label']}** · {source_row['evidence_class']}")
                            st.caption(f"{source_row['use_for']} Historik: {source_row['history']}")

                    sold_library = get_sold_comp_data()
                    consensus = build_multi_source_consensus(research_identity, sold_library)
                    router = build_comp_acquisition_router(research_identity, sold_library)
                    with st.expander("🧭 Nästa bästa comp-källa", expanded=True):
                        r1, r2, r3 = st.columns(3)
                        r1.metric("Exact SOLD", router.get("exact_sold_count", 0))
                        r2.metric("Källor", router.get("source_count", 0))
                        r3.metric("Källquorum", "Ja" if router.get("source_quorum") else "Nej")
                        st.write(f"**Nästa steg:** {router.get('reason')}")
                        for coverage_row in router.get("coverage") or []:
                            st.caption(f"{coverage_row['label']}: {coverage_row['count']} exact SOLD")
                        next_source = router.get("next_source") or {}
                        if next_source.get("direct_query_url"):
                            st.link_button(
                                f"Sök nästa källa: {next_source.get('label')} ↗",
                                next_source["direct_query_url"],
                                use_container_width=True,
                            )
                        elif next_source.get("research_url"):
                            st.link_button(
                                f"Öppna nästa källa: {next_source.get('label')} ↗",
                                next_source["research_url"],
                                use_container_width=True,
                            )
                        st.caption(router.get("note") or "")

                    with st.expander("🌐 Multi-Source Comp Consensus", expanded=False):
                        c1,c2,c3=st.columns(3)
                        c1.metric("Exact SOLD", consensus.get("exact_sold_count",0))
                        c2.metric("Källor", consensus.get("source_count",0))
                        c3.metric("Konsensus", f"{consensus['weighted_median_sek']:.0f} kr" if consensus.get("weighted_median_sek") is not None else "Otillräckligt underlag")
                        if consensus.get("tradera_median_sek") is not None:
                            st.write(f"**Tradera median:** {consensus['tradera_median_sek']:.0f} kr")
                        if consensus.get("international_median_sek") is not None:
                            st.write(f"**Internationell median:** {consensus['international_median_sek']:.0f} kr")
                        divergence=consensus.get("local_vs_international_divergence_pct")
                        if divergence is not None:
                            if divergence >= 25:
                                st.warning(f"Svensk och internationell prisbild skiljer sig med cirka {divergence:.0f} %. Kontrollera lokal efterfrågan innan värderingen används.")
                            else:
                                st.caption(f"Svensk/internationell avvikelse: cirka {divergence:.0f} %.")
                        for source_row in consensus.get("sources") or []:
                            st.caption(f"{source_row['source']}: {source_row['count']} sale(s) · median {source_row['median_sek']:.0f} kr")
                        st.caption(consensus.get("note") or "")

                    ebay_url = ebay_sold_search_url(research_identity)
                    source_by_key = {source["key"]: source for source in sold_source_registry()}
                    research_links=[]
                    tradera_url=next((r.get("direct_query_url") for r in comp_plan["sources"] if r.get("key")=="tradera_sold"),None)
                    if tradera_url:
                        research_links.append(("Tradera ↗",tradera_url))
                    if ebay_url:
                        research_links.append(("eBay Sold ↗",ebay_url))
                    for key,label in [
                        ("card_ladder","Card Ladder ↗"),
                        ("fanatics_collect","Fanatics ↗"),
                        ("comc","COMC ↗"),
                        ("130point","130 Point ↗"),
                        ("sportscardspro","SportsCardsPro ↗"),
                        ("ebay_price_guide","eBay Price Guide ↗"),
                    ]:
                        source=source_by_key.get(key)
                        if source:
                            research_links.append((label,source["research_url"]))
                    for start in range(0,len(research_links),4):
                        cols=st.columns(4)
                        for col,(label,url) in zip(cols,research_links[start:start+4]):
                            col.link_button(label,url,use_container_width=True)
                    st.caption(
                        "Tradera-sökningen kan visa aktiva annonser. De är utbud, inte SOLD. FlipFynds konsensus räknar bara exact identity + explicit sålda poster som redan verifierats/importerats."
                    )

                    with st.expander("⚡ Comp Research Cockpit – snabbare research", expanded=True):
                        workbench = build_research_links(research_identity)
                        st.caption("Öppna flera relevanta källor från exakt strukturerad identitet. Ingen aktiv annons eller prisguide räknas automatiskt som SOLD.")
                        if workbench.get("query"):
                            st.code(workbench["query"], language=None)
                        links = workbench.get("links") or []
                        for start in range(0, len(links), 4):
                            cols = st.columns(4)
                            for col, link in zip(cols, links[start:start+4]):
                                col.link_button(f"{link['label']} ↗", link["url"], use_container_width=True)

                        if sportscardspro_api_configured():
                            if st.button("Hämta SportsCardsPro guidevärde", key=f"scp_context_{selected_label}", use_container_width=True):
                                try:
                                    scp = fetch_sportscardspro_context(research_identity)
                                    if scp.get("ok"):
                                        st.session_state["scp_context_result"] = scp
                                    else:
                                        st.warning(scp.get("error") or "SportsCardsPro kunde inte hämtas.")
                                except Exception as exc:
                                    st.warning(f"SportsCardsPro kunde inte hämtas: {exc}")
                            scp = st.session_state.get("scp_context_result")
                            if isinstance(scp, dict) and scp.get("ok"):
                                st.write(f"**{scp.get('product_name') or 'SportsCardsPro-match'}** · {scp.get('set_name') or ''}")
                                sc1, sc2 = st.columns(2)
                                sc1.metric("Ungraded guide (USD)", f"${scp['ungraded_usd']:.2f}" if scp.get("ungraded_usd") is not None else "Saknas")
                                sc2.metric("PSA 10 guide (USD)", f"${scp['psa_10_usd']:.2f}" if scp.get("psa_10_usd") is not None else "Saknas")
                                st.caption(scp.get("note") or "")
                        else:
                            st.caption("SportsCardsPro API kan aktiveras med Streamlit-secret `SPORTSCARDSPRO_TOKEN`. API-värdet används bara som guide/context, aldrig som SOLD.")

                        st.markdown("**Batchregistrera flera verifierade exact SOLD**")
                        st.caption("En rad per sale: `källa | pris | valuta | fx till SEK | datum | URL`. FX lämnas tom för SEK. Exempel: `eBay | 2.15 | USD | 9.50 | 2026-09-01 | https://...`")
                        with st.form("batch_verified_sold_form", clear_on_submit=True):
                            batch_text = st.text_area("Klistra in verifierade sales", height=130, placeholder="eBay | 2.15 | USD | 9.50 | 2026-09-01 | https://...\nTradera | 24 | SEK | | 2026-08-20 | https://...")
                            batch_identity_source = st.text_input("Källa för identitetskontrollen", key="batch_identity_source", placeholder="t.ex. checklist + foto")
                            b1, b2 = st.columns(2)
                            batch_identity_verified = b1.checkbox("Exakt kortidentitet är verifierad", key="batch_identity_verified")
                            batch_sales_confirmed = b2.checkbox("Varje rad är en faktisk genomförd försäljning", key="batch_sales_confirmed")
                            batch_submit = st.form_submit_button("Importera verifierade sales", type="primary", use_container_width=True)
                        if batch_submit:
                            parsed = parse_verified_sales_batch(
                                batch_text,
                                research_identity,
                                identity_verified=batch_identity_verified,
                                identity_evidence_source=batch_identity_source,
                                sales_confirmed=batch_sales_confirmed,
                            )
                            if parsed.get("errors"):
                                for error in parsed["errors"][:8]:
                                    st.error(error)
                            if parsed.get("rows"):
                                result = acquire_sold_batch(
                                    parsed["rows"],
                                    existing=_load_sold_comp_records(),
                                    source_key="batch_research_workbench",
                                )
                                if result.get("added_count"):
                                    _save_sold_comp_records(result["records"])
                                    get_sold_comp_data.clear()
                                    clear_analysis_cache()
                                    st.session_state["result_cache"] = {}
                                    st.success(f"{result['added_count']} verifierade sale(s) sparades. Kör om analysen för att använda det nya underlaget.")
                                elif result.get("duplicate_count"):
                                    st.info("Alla giltiga rader fanns redan i sold-comp-biblioteket.")

                    defaults = build_quick_capture_defaults(research_identity)
                    with st.form("manual_sold_research_form", clear_on_submit=True):
                        st.markdown("**Snabbregistrera verifierat avslut**")
                        st.caption("Identiteten är redan förifylld från kandidatkortet. Du fyller bara i sådant FlipFynd inte får gissa.")
                        f1, f2 = st.columns(2)
                        sold_price = f1.number_input("Sålt pris", min_value=0.0, step=1.0, value=defaults["sold_price"])
                        currency = f2.selectbox("Valuta", ["SEK", "USD", "EUR", "GBP"], index=0)
                        f3, f4 = st.columns(2)
                        source_platform = f3.selectbox(
                            "Källa",
                            ["Tradera", "eBay", "eBay Product Research", "Card Ladder", "Fanatics Collect", "COMC", "130 Point", "SportsCardsPro", "Annan verifierad källa"],
                        )
                        shipping_text = f4.text_input("Frakt (valfritt)", value="")
                        fx_rate_text = ""
                        if currency != "SEK":
                            fx_rate_text = st.text_input(
                                "Explicit valutakurs till SEK",
                                value="",
                                help="Obligatoriskt för annan valuta än SEK. FlipFynd hämtar eller gissar aldrig valutakursen.",
                            )
                        sold_url = st.text_input("Länk till försäljningen", value=defaults["sold_url"])
                        sold_at = st.text_input("Såld datum/tid (valfritt)", value=defaults["sold_at"], help="Exempel: 2026-09-08")
                        identity_source = st.text_input(
                            "Källa för identitetskontrollen",
                            value="",
                            help="Exempel: checklist publisher, grading label eller manuell bildkontroll.",
                        )
                        identity_verified = st.checkbox(
                            "Jag har verifierat exakt kortidentitet",
                            value=False,
                            help="Kryssa bara om spelare, set, säsong, kortnummer och relevant variant verkligen stämmer.",
                        )
                        sale_confirmed = st.checkbox(
                            "Jag har verifierat att detta var en faktisk genomförd försäljning",
                            value=False,
                        )
                        submitted = st.form_submit_button("Spara verifierat avslut", type="primary", use_container_width=True)

                    if submitted:
                        try:
                            shipping_value = None if not shipping_text.strip() else shipping_text.strip().replace(",", ".")
                            manual_row = build_manual_sold_row(
                                research_identity,
                                sold_price=sold_price,
                                currency=currency,
                                source_platform=source_platform,
                                sold_url=sold_url,
                                sold_at=sold_at,
                                shipping=shipping_value,
                                fx_rate_to_sek=(None if currency == "SEK" else fx_rate_text.strip().replace(",", ".")),
                                identity_verified=identity_verified,
                                identity_evidence_source=identity_source,
                                sale_confirmed=sale_confirmed,
                            )
                            result = acquire_sold_batch(
                                [manual_row],
                                existing=_load_sold_comp_records(),
                                source_key="manual_research_assist",
                            )
                            if result["added_count"]:
                                _save_sold_comp_records(result["records"])
                                get_sold_comp_data.clear()
                                clear_analysis_cache()
                                st.session_state["result_cache"] = {}
                                status = "exact-ready" if result["exact_ready_count"] else "sparat för fortsatt identitetsgranskning"
                                st.success(f"Avslutet sparades · {status}. Kör om analysen för att använda det nya underlaget.")
                            elif result["duplicate_count"]:
                                st.info("Det här avslutet finns redan i sold-comp-biblioteket.")
                            elif result["quarantine_count"]:
                                st.error("Avslutet kunde inte sparas. Kontrollera pris, valuta och obligatoriska fält.")
                        except Exception as exc:
                            st.error(f"Avslutet kunde inte registreras: {exc}")

            template = (
                "title,sold_price,currency,sold_at,url,sport,sale_status,"
                "player_name,set_name,season,card_number,parallel,serial_denominator,"
                "grading_company,grade,identity_verified,identity_evidence_source\n"
            ).encode("utf-8")
            st.download_button(
                "⬇️ Hämta mall för verifierade sold comps",
                data=template,
                file_name="flipfynd_sold_comp_template.csv",
                mime="text/csv",
                use_container_width=True,
                help="Mallen innehåller även strukturerad kortidentitet så importerade avslut kan bli exact-ready efter verifiering.",
            )

        st.caption(
            "Viktigt: lagring i själva Streamlit-instansen är runtime-lagring. Exportfunktionen gör att sold-comp-historiken "
            "kan bevaras tills en extern persistent databas kopplas in."
        )

    with st.expander("📒 Flip Journal & Feedback Loop", expanded=False):
        current_health = _cached_storage_probe(DATABASE_URL) if DATABASE_URL else storage_status(None)
        journal_pending = get_pending(PENDING_SYNC_PATH, "flip_journal") is not None
        if current_health.durable and not journal_pending and not st.session_state.get("storage_error_flip_journal"):
            st.caption("💾 Lagring: persistent PostgreSQL · synkad")
        elif journal_pending:
            st.caption("⚠️ Lagring: lokal väntande ändring · inte synkad till PostgreSQL ännu")
        else:
            st.caption("💾 Lagring: lokal runtime (inte garanterat persistent i Streamlit Cloud)")
        journal_rows = _load_flip_journal_records()
        metrics = journal_metrics(journal_rows)
        st.caption("Här jämför FlipFynd sina prognoser med verkliga köp och försäljningar. Journalen påverkar ännu inte rekommendationerna automatiskt – den samlar först kalibreringsdata.")
        j1, j2, j3, j4 = st.columns(4)
        j1.metric("Loggade affärer", metrics["entry_count"])
        j2.metric("Sålda", metrics["sold_count"])
        j3.metric("Verklig nettovinst", f"{metrics['actual_net_profit_total']:.0f} kr")
        j4.metric("Träffgrad", f"{metrics['win_rate']:.0f}%" if metrics["win_rate"] is not None else "Ej bedömd")
        if metrics["median_days_to_sell"] is not None:
            st.caption(f"Median faktisk säljtid: {metrics['median_days_to_sell']} dagar.")
        if metrics["mean_profit_error"] is not None:
            direction = "underskattar" if metrics["mean_profit_error"] > 0 else "överskattar"
            st.caption(f"Kalibreringssignal: modellen {direction} i snitt nettovinsten med {abs(metrics['mean_profit_error']):.0f} kr på avslutade journalposter.")

        dashboard = build_calibration_dashboard(journal_rows)
        st.markdown("### 📊 Kalibreringsdashboard")
        st.caption(dashboard["note"])
        st.markdown(f"**{dashboard['headline']}**")
        st.caption(dashboard["next_action"])

        overall = dashboard["overall"]
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Avslut", dashboard["sold_count"])
        d2.metric("Lönsamma", f"{overall['win_rate']:.0f}%" if overall.get("win_rate") is not None else "–")
        d3.metric("Median nettovinst", f"{overall['median_net_profit']:.0f} kr" if overall.get("median_net_profit") is not None else "–")
        d4.metric("Median säljtid", f"{overall['median_days_to_sell']:.0f} dagar" if overall.get("median_days_to_sell") is not None else "–")

        overview_tab, wins_tab, misses_tab = st.tabs(["Översikt", "Vad fungerar", "Vad går fel"])
        with overview_tab:
            gate = overall["sample"]
            st.markdown(f"**Datamognad: {gate['label']}**")
            st.caption(gate["message"])
            if dashboard["review_rate_pct"] is not None:
                st.caption(f"Outcome Review: {dashboard['reviewed_count']} av {dashboard['sold_count']} avslut ({dashboard['review_rate_pct']:.0f}%).")
            if dashboard.get("best_tendency"):
                best = dashboard["best_tendency"]
                st.success(f"Starkaste observerade tendensen: {best['label']} · median nettovinst {best['median_net_profit']:.0f} kr på {best['count']} avslut.")
            else:
                st.info("Ingen signal har ännu tillräckligt underlag för att visas som historisk tendens.")
            for item in dashboard["attention"]:
                st.warning(f"**{item['title']}** – {item['message']}")
            if overall["sample"]["supports_adjustment_review"]:
                st.warning("20+ avslut finns. Modellvikter får nu granskas manuellt, men FlipFynd ändrar dem fortfarande inte automatiskt.")

        with wins_tab:
            eligible_groups = [g for g in dashboard["groups"] if g["sample"]["supports_description"]]
            if eligible_groups:
                for group in eligible_groups[:12]:
                    profit_text = f"{group['median_net_profit']:.0f} kr" if group.get("median_net_profit") is not None else "–"
                    win_text = f"{group['win_rate']:.0f}%" if group.get("win_rate") is not None else "–"
                    days_text = f"{group['median_days_to_sell']:.0f} dagar" if group.get("median_days_to_sell") is not None else "–"
                    st.write(f"**{group['label']}** · {group['count']} avslut · {win_text} lönsamma · median {profit_text} · {days_text}")
                    if group["sample"]["supports_tendency"]:
                        st.caption("✅ Tillräckligt många avslut för en historisk tendens. Det bevisar inte orsakssamband.")
                    else:
                        st.caption(f"🟡 {group['sample']['message']}")
            else:
                st.info("Minst 5 avslut behövs innan FlipFynd visar grundläggande utfall per signal.")

        with misses_tab:
            miss_analysis = dashboard["miss_analysis"]
            if miss_analysis["sold_count"]:
                m1, m2, m3 = st.columns(3)
                m1.metric("Avslut analyserade", miss_analysis["sold_count"])
                m2.metric("Med tydlig avvikelse", miss_analysis["rows_with_miss"])
                miss_rate = miss_analysis.get("miss_rate_pct")
                m3.metric("Avvikelseandel", f"{miss_rate:.0f}%" if miss_rate is not None else "–")
                if miss_analysis["groups"]:
                    for group in miss_analysis["groups"][:8]:
                        suffix = " · mönster kan granskas" if group["enough_for_pattern"] else " · för litet underlag för mönsterslutsats"
                        st.write(f"**{group['label']}** · {group['count']} avslut ({group['share_of_sold_pct']:.0f}%){suffix}")
                    if miss_analysis.get("primary_pattern"):
                        primary = miss_analysis["primary_pattern"]
                        st.warning(f"Vanligaste återkommande missen: **{primary['label']}** ({primary['count']} avslut). Detta är granskningsunderlag, inte en automatisk viktändring.")
                else:
                    st.success("Inga tydliga avvikelser kan identifieras från de sparade journalfälten hittills.")
            else:
                st.info("Missanalysen aktiveras när det finns avslutade journalposter med verkligt nettoresultat.")

        false_positive = build_false_positive_review(journal_rows)
        with st.expander("🎯 False Positive Review – vilka KÖP blev dåliga affärer?", expanded=False):
            st.caption(false_positive["note"])
            fp1, fp2, fp3 = st.columns(3)
            fp1.metric("Avslutade KÖP", false_positive["completed_buy_recommendations"])
            fp2.metric("Falskt positiva utfall", false_positive["false_positive_count"])
            rate = false_positive.get("false_positive_rate_pct")
            fp3.metric("Andel", f"{rate:.0f}%" if rate is not None else "–")
            if not false_positive["completed_buy_recommendations"]:
                st.info("Här behövs avslutade affärer som hade KÖP-rekommendation när de loggades.")
            elif not false_positive["supports_pattern_review"]:
                st.info("Minst 5 avslutade KÖP-affärer behövs innan FlipFynd börjar visa återkommande mönster.")
            else:
                eligible_segments = [x for x in false_positive["segments"] if x["enough_for_pattern"]]
                if eligible_segments:
                    st.markdown("**Var uppstår falskt positiva KÖP?**")
                    for segment in eligible_segments[:8]:
                        st.write(
                            f"**{segment['label']}** · {segment['false_positive_count']} av "
                            f"{segment['eligible_count']} ({segment['false_positive_rate_pct']:.0f}%) falskt positiva utfall"
                        )
                else:
                    st.caption("Det finns ännu inget enskilt segment med minst 5 avslutade KÖP-affärer.")
                losses = false_positive["reason_counts"].get("actual_loss", 0)
                misses = false_positive["reason_counts"].get("large_profit_shortfall", 0)
                st.caption(f"Utfallssignaler: {losses} faktisk förlust · {misses} stor dokumenterad vinstmiss. Samma affär kan ingå i båda.")
            st.warning("Detta är ett granskningslager. Det ändrar inte fyndscore, beslut eller modellvikter automatiskt.")

        false_negative = build_false_negative_review(journal_rows)
        with st.expander("🔎 False Negative Review – vilka bra affärer missade FlipFynd?", expanded=False):
            st.caption(false_negative["note"])
            fn1, fn2, fn3 = st.columns(3)
            fn1.metric("Avslut utan KÖP", false_negative["completed_non_buy_recommendations"])
            fn2.metric("Missade starka fynd", false_negative["false_negative_count"])
            rate = false_negative.get("false_negative_rate_pct")
            fn3.metric("Andel", f"{rate:.0f}%" if rate is not None else "–")
            if not false_negative["completed_non_buy_recommendations"]:
                st.info("Här behövs avslutade affärer som ursprungligen var KANSKE eller AVSTÅ.")
            elif not false_negative["supports_pattern_review"]:
                st.info("Minst 5 avslut utan KÖP behövs innan FlipFynd börjar visa återkommande mönster.")
            else:
                eligible_segments = [x for x in false_negative["segments"] if x["enough_for_pattern"]]
                if eligible_segments:
                    st.markdown("**Var verkar FlipFynd vara för försiktig?**")
                    for segment in eligible_segments[:10]:
                        st.write(f"**{segment['label']}** · {segment['false_negative_count']} av {segment['eligible_count']} ({segment['false_negative_rate_pct']:.0f}%) blev starka verkliga vinnare")
                else:
                    st.caption("Det finns ännu inget enskilt segment med minst 5 avslut.")
            st.warning("Detta visar möjliga missade fynd. Det bevisar inte att en säkerhetsregel är fel och ändrar inga vikter automatiskt.")

        model_review = build_model_review_dashboard(journal_rows)
        with st.expander("🧭 Model Review – fungerar besluten i verkligheten?", expanded=False):
            st.caption(model_review["note"])
            mr1, mr2, mr3 = st.columns(3)
            mr1.metric("Verkliga avslut", model_review["sold_count"])
            clean = model_review.get("buy_without_false_positive_rate_pct")
            mr2.metric("KÖP utan tydlig miss", f"{clean:.0f}%" if clean is not None else "–")
            miss = model_review.get("false_negative_rate_pct")
            mr3.metric("Missade starka vinnare", f"{miss:.0f}%" if miss is not None else "–")

            if not model_review["sold_count"]:
                st.info("Model Review aktiveras när verkliga affärer har avslutats i Flip Journal.")
            else:
                st.markdown("**Hur gick besluten i verkligheten?**")
                for row in model_review["decision_summary"]:
                    if not row["count"]:
                        continue
                    win = row.get("profitable_rate_pct")
                    profit = row.get("median_actual_net_profit")
                    st.write(f"**{row['decision']}** · {row['count']} avslut · {win:.0f}% lönsamma · median {profit:.0f} kr" if win is not None and profit is not None else f"**{row['decision']}** · {row['count']} avslut")

                reviewable = [x for x in model_review["signals"] if x["reviewable"]]
                if reviewable:
                    st.markdown("**Signaler att granska**")
                    for sig in reviewable[:10]:
                        parts=[]
                        if sig["enough_buy_sample"]:
                            parts.append(f"{sig['false_positive_rate_pct']:.0f}% dåliga KÖP ({sig['completed_buy_count']} avslut)")
                        if sig["enough_non_buy_sample"]:
                            parts.append(f"{sig['false_negative_rate_pct']:.0f}% missade vinnare ({sig['completed_non_buy_count']} avslut)")
                        st.write(f"**{sig['label']}** · " + " · ".join(parts))

                if model_review["supports_manual_model_review"]:
                    st.warning("20+ verkliga avslut finns. Nu finns underlag för manuell modellgranskning – inte automatisk viktändring.")
                else:
                    remaining=max(0, model_review["min_manual_review_sample"]-model_review["sold_count"])
                    st.info(f"Samla {remaining} ytterligare verkliga avslut innan modellvikter ens bör övervägas manuellt.")

        capital_validation = build_capital_efficiency_validation(journal_rows)
        with st.expander("💸 Capital Efficiency – fungerar den i verkligheten?", expanded=False):
            st.caption(capital_validation["note"])
            cv1, cv2, cv3 = st.columns(3)
            cv1.metric("Avslut med sparad kapitalpoäng", capital_validation["captured_completed_count"])
            cv2.metric("Äldre/utan kapitalpoäng", capital_validation["legacy_or_unscored_completed_count"])
            cv3.metric("Redo för manuell granskning", "Ja" if capital_validation["supports_manual_review"] else "Nej")

            high = capital_validation["high"]
            lower = capital_validation["lower"]
            if capital_validation["captured_completed_count"] == 0:
                st.info("Valideringen startar först när nya affärer med sparad Capital Efficiency har sålts.")
            else:
                st.markdown("**Verkligt utfall efter kapitalpoäng**")
                for label, cohort in (("65–100", high), ("0–64", lower)):
                    if not cohort["count"]:
                        continue
                    win = cohort.get("win_rate_pct")
                    p30 = cohort.get("median_actual_profit_30d")
                    days = cohort.get("median_days_to_sell")
                    parts = [f"{cohort['count']} avslut"]
                    if win is not None: parts.append(f"{win:.0f}% lönsamma")
                    if p30 is not None: parts.append(f"{p30:.0f} kr verklig medianvinst/30 dagar")
                    if days is not None: parts.append(f"{days:.0f} dagar median")
                    st.write(f"**Kapitalpoäng {label}** · " + " · ".join(parts))

                direction = capital_validation.get("direction")
                if direction == "supports":
                    st.success("Hög kapitalpoäng har hittills gett bättre realiserad vinsttakt i de jämförbara grupperna.")
                elif direction == "challenges":
                    st.warning("Hög kapitalpoäng har hittills inte gett bättre realiserad vinsttakt. Modellen bör granskas innan den får större vikt.")
                elif direction == "mixed":
                    st.info("Grupperna är hittills ungefär lika i realiserad vinsttakt.")
                else:
                    st.info("Minst 5 avslut behövs i både hög och lägre kapitalpoäng innan grupperna jämförs.")

                if capital_validation["supports_manual_review"]:
                    st.warning("20+ relevanta avslut och minst 5 i båda grupperna finns. Manuell modellgranskning är nu rimlig; inga vikter ändras automatiskt.")
                else:
                    remaining=max(0, capital_validation["min_review_sample"]-capital_validation["captured_completed_count"])
                    st.caption(f"Minst {remaining} ytterligare relevanta avslut behövs för 20-observationsgränsen, och båda grupperna måste ha minst 5.")

        prediction_validation = build_prediction_outcome_validation(journal_rows)
        with st.expander("🎯 Prognos mot verklighet – var har FlipFynd fel?", expanded=False):
            st.caption(prediction_validation["note"])
            p1, p2 = st.columns(2)
            p1.metric("Verkliga avslut", prediction_validation["sold_count"])
            p2.metric("Redo för manuell granskning", "Ja" if prediction_validation["review_ready"] else "Nej")
            for key, label, unit in (("profit","Nettovinst"," kr"),("roi","ROI"," %"),("days_to_sell","Säljtid"," dagar")):
                m=prediction_validation[key]
                if not m["count"]:
                    st.write(f"**{label}:** inget jämförbart underlag ännu")
                    continue
                st.write(f"**{label}** · {m['count']} jämförelser · medianfel {m['median_error']:+.1f}{unit} · typiskt fel {m['median_abs_error']:.1f}{unit}")
                if not m["enough"]:
                    st.caption("Minst 5 jämförbara avslut krävs innan riktningen tolkas.")
                elif key=="days_to_sell":
                    st.caption("Kort tar i median längre tid att sälja än prognosen." if m["bias"]=="underestimated" else ("Kort säljs i median snabbare än prognosen." if m["bias"]=="overestimated" else "Säljtidsprognosen är balanserad i median."))
                else:
                    st.caption("FlipFynd har i median varit för optimistisk." if m["bias"]=="overestimated" else ("FlipFynd har i median varit för försiktig." if m["bias"]=="underestimated" else "Prognosen är balanserad i median."))
            st.warning("Diagnostiken ändrar inga modellvikter automatiskt.")

        error_segmentation = build_error_segmentation(journal_rows)
        with st.expander("🧩 Fel per typ av kort – var missar FlipFynd?", expanded=False):
            st.caption(error_segmentation["note"])
            es1, es2 = st.columns(2)
            es1.metric("Verkliga avslut", error_segmentation["sold_count"])
            es2.metric("Segment redo att granska", error_segmentation["reviewable_count"])
            labels = {
                "sport":"Sport","price_band":"Prisklass","risk_band":"Risk",
                "sellability_band":"Säljbarhet","valuation_confidence":"Värderingssäkerhet",
                "exact_comp":"Exakt comp","rookie_signal":"Rookie","market_edge":"Market Edge",
                "information_edge":"Information Edge",
            }
            if not error_segmentation["reviewable"]:
                st.info("Minst 5 jämförbara verkliga utfall behövs inom ett segment innan det listas här.")
            else:
                for seg in error_segmentation["reviewable"][:12]:
                    st.write(f"**{labels.get(seg['segment'], seg['segment'])}: {seg['label']}** · {seg['count']} avslut")
                    parts=[]
                    if seg["profit"]["count"]:
                        parts.append(f"vinstfel {seg['profit']['median_error']:+.0f} kr")
                    if seg["roi"]["count"]:
                        parts.append(f"ROI-fel {seg['roi']['median_error']:+.0f} %-enheter")
                    if seg["days_to_sell"]["count"]:
                        parts.append(f"säljtid {seg['days_to_sell']['median_error']:+.0f} dagar")
                    if parts:
                        st.caption(" · ".join(parts))
            metric_reviews = error_segmentation.get("reviewable_by_metric") or {}
            if any(metric_reviews.values()):
                st.markdown("**Största typiska fel – per måttenhet**")
                metric_labels = [("profit","Vinst","kr"),("roi","ROI","%-enheter"),("velocity","Säljtid","dagar")]
                metric_keys = {"profit":"profit","roi":"roi","velocity":"days_to_sell"}
                for metric_key, metric_title, unit in metric_labels:
                    ranked = metric_reviews.get(metric_key) or []
                    if ranked:
                        top = ranked[0]
                        metric = top[metric_keys[metric_key]]
                        st.caption(f"{metric_title}: {labels.get(top['segment'],top['segment'])} – {top['label']} · median absolutfel {metric['median_abs_error']:.0f} {unit}")
            st.warning("Segmenteringen är diagnostik. Kr, %-enheter och dagar hålls separata och ändrar inga modellvikter automatiskt.")

        correction_review = build_model_correction_candidates(error_segmentation)
        with st.expander("🛠️ Modellförslag – vad bör granskas?", expanded=False):
            st.caption(correction_review["note"])
            mc1, mc2 = st.columns(2)
            mc1.metric("Kandidater", correction_review["count"])
            mc2.metric("Starka kandidater", correction_review["strong_count"])
            if not correction_review["candidates"]:
                st.info("Inget segment har ännu både tillräckligt underlag och ett tydligt systematiskt prognosfel.")
            else:
                segment_names={"sport":"Sport","price_band":"Prisklass","risk_band":"Risk","sellability_band":"Säljbarhet",
                    "valuation_confidence":"Värderingssäkerhet","exact_comp":"Exakt comp","rookie_signal":"Rookie",
                    "market_edge":"Market Edge","information_edge":"Information Edge"}
                for c in correction_review["candidates"][:10]:
                    st.write(f"**{c['strength']}: {segment_names.get(c['segment'],c['segment'])} – {c['label']}** · {c['count']} avslut")
                    st.caption(c["suggestion"].capitalize() + ".")
            st.warning("Detta är granskningsförslag, inte modelländringar. FlipFynd ändrar inga vikter, haircuts eller köpbeslut automatiskt.")

        correction_sim = build_correction_simulation(journal_rows, correction_review)
        with st.expander("🧪 Korrigeringssimulator – hade ändringen faktiskt hjälpt?", expanded=False):
            st.caption(correction_sim["note"])
            cs1, cs2 = st.columns(2)
            cs1.metric("Testade kandidater", correction_sim["tested_count"])
            cs2.metric("Klarade första filtret", correction_sim["passed_count"])
            if not correction_sim["results"]:
                st.info("Det finns ännu inga modellkandidater att simulera.")
            else:
                for result in correction_sim["results"][:10]:
                    status="✅ Går vidare" if result["worth_reviewing"] else "⛔ Inte tillräckligt bra"
                    st.write(f"**{status}: {result['label']}** · {result['count']} avslut")
                    for metric_name, m in result["metrics"].items():
                        if not m.get("eligible"):
                            continue
                        display={"profit":"Vinst","roi":"ROI","velocity":"Säljtid"}[metric_name]
                        st.caption(
                            f"{display}: justering {m['shift']:+.1f} · typiskt fel {m['mae_before']:.1f} → {m['mae_after']:.1f} · förbättring {m['improvement_pct']:.0f}%"
                        )
            st.warning("En historisk förbättring räcker inte för produktionsändring. Simulatorn ändrar ingenting automatiskt och samma data används här både för att hitta och testa korrigeringen.")

        holdout_validation = build_holdout_validation(journal_rows, correction_review)
        with st.expander("🧪 Holdout-test – fungerar korrigeringen på separat data?", expanded=False):
            st.caption(holdout_validation["note"])
            hv1, hv2 = st.columns(2)
            hv1.metric("Testade kandidater", holdout_validation["tested_count"])
            hv2.metric("Klarade holdout", holdout_validation["passed_count"])
            if not holdout_validation["results"]:
                st.info("Det finns ännu inga modellkandidater att testa.")
            else:
                for result in holdout_validation["results"][:10]:
                    status="✅ Klarar holdout" if result["passes_holdout"] else "⛔ Klarar inte holdout"
                    st.write(f"**{status}: {result['label']}** · discovery {result['discovery_count']} · holdout {result['holdout_count']}")
                    for metric_name,m in result["metrics"].items():
                        if not m.get("eligible"):
                            continue
                        display={"profit":"Vinst","roi":"ROI","velocity":"Säljtid"}[metric_name]
                        st.caption(f"{display}: justering {m['shift']:+.1f} · holdout-fel {m['mae_before']:.1f} → {m['mae_after']:.1f} · {m['improvement_pct']:.0f}% bättre")
            st.warning("Även en klarad holdout är bara evidens för fortsatt manuell granskning. Ingen produktionsmodell ändras automatiskt.")

        approval_gate = build_correction_approval_gate(holdout_validation)
        with st.expander("🚦 Korrigeringsgrind – vad är redo att överväga?", expanded=False):
            st.caption(approval_gate["note"])
            ag1, ag2 = st.columns(2)
            ag1.metric("Kandidater", approval_gate["candidate_count"])
            ag2.metric("Redo att överväga", approval_gate["review_ready_count"])
            if not approval_gate["reviews"]:
                st.info("Det finns ännu inga holdout-testade korrigeringar att granska.")
            else:
                for review in approval_gate["reviews"][:10]:
                    if review["ready_for_manual_review"]:
                        st.success(f"Redo att överväga: {review['label']} · discovery {review['discovery_count']} · holdout {review['holdout_count']}")
                        for m in review["metrics"]:
                            display={"profit":"Vinst","roi":"ROI","velocity":"Säljtid"}.get(m["metric"],m["metric"])
                            st.caption(f"{display}: fel {m['mae_before']:.1f} → {m['mae_after']:.1f} · {m['improvement_pct']:.0f}% bättre på holdout")
                    else:
                        st.write(f"**Inte redo: {review['label']}**")
                        if review["blockers"]:
                            st.caption(" · ".join(review["blockers"]))
            st.warning("Redo att överväga betyder endast redo för manuell bedömning. Ingen korrigering kan aktiveras här och inga köpbeslut ändras.")

        if journal_rows:
            labels = {f"{r.get('title','Okänd')} · {r.get('status','')} · {r.get('id')}": r.get('id') for r in journal_rows}
            selected_label = st.selectbox("Välj journalpost", list(labels), key="flip_journal_entry")
            selected_id = labels[selected_label]
            selected = next(r for r in journal_rows if r.get("id") == selected_id)
            c1, c2 = st.columns(2)
            with c1:
                purchase_price = st.number_input("Faktisk total inköpskostnad", min_value=0.0, value=float(selected.get("purchase_price") or 0), step=1.0, key=f"jp_{selected_id}")
                purchase_date = st.text_input("Köpdatum (ÅÅÅÅ-MM-DD)", value=selected.get("purchase_date") or "", key=f"jd_{selected_id}")
                sale_price = st.number_input("Faktiskt försäljningspris", min_value=0.0, value=float(selected.get("sale_price") or 0), step=1.0, key=f"js_{selected_id}")
                sale_date = st.text_input("Säljdatum (ÅÅÅÅ-MM-DD)", value=selected.get("sale_date") or "", key=f"jsd_{selected_id}")
            with c2:
                selling_fee = st.number_input("Faktisk försäljningsavgift", min_value=0.0, value=float(selected.get("selling_fee") or 0), step=1.0, key=f"jf_{selected_id}")
                packaging_cost = st.number_input("Emballage", min_value=0.0, value=float(selected.get("packaging_cost") or 0), step=1.0, key=f"jpack_{selected_id}")
                other_cost = st.number_input("Övrig kostnad", min_value=0.0, value=float(selected.get("other_cost") or 0), step=1.0, key=f"jo_{selected_id}")
                notes = st.text_area("Anteckning", value=selected.get("notes") or "", key=f"jn_{selected_id}")

            review_keys = []
            review_note = selected.get("outcome_review_note") or ""
            if selected.get("status") == "sålt" or sale_price > 0:
                with st.expander("🧾 Outcome Review – vad påverkade det verkliga utfallet?", expanded=False):
                    st.caption(
                        "Markera bara sådant du faktiskt vet efter affären. FlipFynd använder inte dessa orsaker om du inte själv markerar dem."
                    )
                    current_review = [
                        key for key in (selected.get("outcome_review_reasons") or [])
                        if key in OUTCOME_REVIEW_REASONS
                    ]
                    selected_labels = st.multiselect(
                        "Verifierade orsaker",
                        options=list(OUTCOME_REVIEW_REASONS.values()),
                        default=[OUTCOME_REVIEW_REASONS[key] for key in current_review],
                        key=f"jor_{selected_id}",
                    )
                    reverse_review = {label: key for key, label in OUTCOME_REVIEW_REASONS.items()}
                    review_keys = [reverse_review[label] for label in selected_labels if label in reverse_review]
                    review_note = st.text_area(
                        "Kort förklaring (valfritt)",
                        value=review_note,
                        key=f"jorn_{selected_id}",
                        help="Exempel: såg efter leverans att kortet var en annan parallel. Skriv bara sådant du själv har verifierat.",
                    )
                    if current_review:
                        st.caption("Tidigare sparad Outcome Review är laddad ovan och kan ändras eller rensas.")

            if st.button("Spara journalpost", type="primary", use_container_width=True, key=f"save_{selected_id}"):
                changes = {"purchase_price":purchase_price,"purchase_date":purchase_date or None,"selling_fee":selling_fee,"packaging_cost":packaging_cost,"other_cost":other_cost,"notes":notes}
                if selected.get("status") == "sålt" or sale_price > 0:
                    changes.update(build_outcome_review_patch(review_keys, review_note))
                if sale_price > 0:
                    changes["sale_price"] = sale_price
                    changes["sale_date"] = sale_date or None
                _save_flip_journal_records(update_entry(journal_rows, selected_id, **changes))
                st.success("Journalpost sparad.")
                st.rerun()
        journal_export = json.dumps({"schema_version":5,"entries":journal_rows}, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button("Exportera Flip Journal", data=journal_export, file_name="flipfynd_flip_journal.json", mime="application/json", use_container_width=True, help="Spara en kopia. Streamlit Clouds lokala runtime-lagring är inte permanent mellan alla omstarter/deploys.")
        journal_health = _cached_storage_probe(DATABASE_URL) if DATABASE_URL else storage_status(None)
        journal_pending = get_pending(PENDING_SYNC_PATH, "flip_journal") is not None
        if journal_health.durable and not journal_pending and not st.session_state.get("storage_error_flip_journal"):
            st.success("Journalen använder persistent PostgreSQL-lagring och är synkad.")
        elif journal_pending:
            st.error("Journalen har en osynkroniserad lokal ändring. FlipFynd fortsätter visa den lokala versionen tills synkning lyckas.")
            st.caption("Den väntande kopian är runtime-lokal och kan gå förlorad vid omstart/deploy. Exportera journalen om databasen är nere en längre stund.")
        else:
            st.warning("Journalen använder lokal runtime-lagring just nu. Exportera den regelbundet tills persistent databas är aktiv och nåbar.")
        if st.session_state.get("storage_error_flip_journal"):
            st.caption("Databasen kunde inte nås vid senaste journaloperationen. FlipFynd sparade därför en explicit väntande lokal kopia i stället för att låtsas att synkningen lyckades.")

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
        try:
            from src.player_market import load_player_market
            kb_cov = knowledge_coverage(load_player_market())
            with st.expander("Spelarkunskap – täckning", expanded=False):
                for sport_key, label in (("hockey","Hockey"),("football","Fotboll")):
                    info=kb_cov.get(sport_key,{})
                    st.caption(
                        f"{label}: {info.get('covered_players',0)}/{info.get('known_players',0)} spelare "
                        f"({info.get('coverage_pct',0):.1f} %) har verifierad Player Knowledge."
                    )
                st.caption("Saknad spelarkunskap gissas inte; den lämnas okänd tills den verifierats.")
        except Exception:
            pass


# SELLER_TOP5_UI_V1
# Restore Seller Top 5 form values after a Streamlit websocket/session reset.
try:
    _seller_qp_alias = str(st.query_params.get("seller", "") or "").strip()
    _seller_qp_profile = str(st.query_params.get("seller_profile", "") or "").strip()
except Exception:
    _seller_qp_alias = ""
    _seller_qp_profile = ""
if "seller_top5_alias" not in st.session_state and _seller_qp_alias:
    st.session_state["seller_top5_alias"] = _seller_qp_alias
if "seller_top5_profile_url" not in st.session_state and _seller_qp_profile:
    st.session_state["seller_top5_profile_url"] = _seller_qp_profile


def _clear_seller_top5_ui():
    old_alias = str(st.session_state.get("seller_top5_alias") or "").strip()
    old_profile = str(st.session_state.get("seller_top5_profile_url") or "").strip()
    reset_seller_top5_search(
        old_alias,
        old_profile,
        database_url=DATABASE_URL,
        session=st.session_state,
    )
    for key in ("seller_top5_result", "seller_top5_alias", "seller_top5_profile_url"):
        st.session_state.pop(key, None)
    try:
        for key in ("seller", "seller_profile"):
            if key in st.query_params:
                del st.query_params[key]
    except Exception:
        pass


_seller_existing_result = st.session_state.get("seller_top5_result") or {}
_seller_existing_status = str(_seller_existing_result.get("status") or "")
_seller_search_needs_attention = _seller_existing_status in {"INVENTORY_PARTIAL", "PROFILE_INCOMPLETE"}

with st.sidebar.expander("🏪 Säljare – Top 5 kort", expanded=_seller_search_needs_attention):
    st.caption("Läs in en Tradera-säljare och se de bästa korten medan sökningen fortsätter.")
    seller_top5_alias = st.text_input("Säljare (valfritt)", key="seller_top5_alias", placeholder="hämtas automatiskt från profillänken")
    seller_top5_profile_url = st.text_input(
        "Tradera-profil",
        key="seller_top5_profile_url",
        placeholder="https://www.tradera.com/profile/items/...",
        help="Klistra in säljarens profilsida, till exempel https://www.tradera.com/profile/items/5412219/",
    )
    try:
        if seller_top5_alias and str(st.query_params.get("seller", "") or "") != str(seller_top5_alias):
            st.query_params["seller"] = str(seller_top5_alias)
        if seller_top5_profile_url and str(st.query_params.get("seller_profile", "") or "") != str(seller_top5_profile_url):
            st.query_params["seller_profile"] = str(seller_top5_profile_url)
    except Exception:
        pass
    seller_top5_sport_label = "Alla"
    seller_top5_profile_url_resolved = str(seller_top5_profile_url or "").strip()
    _profile_alias = str(seller_top5_alias or "").strip()
    if seller_top5_profile_url_resolved and _profile_alias:
        _profile_base, _profile_sep, _profile_query = seller_top5_profile_url_resolved.partition("?")
        _profile_clean = _profile_base.rstrip("/")
        if "/profile/items/" in _profile_clean and _profile_clean.rsplit("/", 1)[-1].isdigit():
            _profile_base = _profile_clean + "/" + _profile_alias.replace(" ", "%20")
            seller_top5_profile_url_resolved = _profile_base + ((_profile_sep + _profile_query) if _profile_sep else "")
    _seller_previous_result = _seller_existing_result
    _seller_continue_inventory = str(_seller_previous_result.get("status") or "") in {"INVENTORY_PARTIAL", "PROFILE_INCOMPLETE"}
    _seller_button_label = "Fortsätt söka" if _seller_continue_inventory else "🔎 Hitta säljarens bästa kort"
    if st.button(_seller_button_label, key="seller_top5_run", use_container_width=True):
        alias = str(seller_top5_alias or "").strip()
        if not alias and not seller_top5_profile_url_resolved:
            st.warning("Klistra in en Tradera-profillänk eller ange ett säljarnamn.")
        else:
            creds = _resolve_tradera_api_credentials()
            sport_key = "all"
            local_market = get_data(get_data_version())
            seller_status = st.status(f"🔎 Söker {alias}", expanded=False)
            seller_progress_line = seller_status.empty()
            seller_progress_bar = st.progress(0, text="Startar…")

            def _seller_search_progress(info):
                phase = str((info or {}).get("phase") or "")
                page = int((info or {}).get("page") or 0)
                found = int((info or {}).get("found_count") or 0)
                pages_read = int((info or {}).get("pages_read") or 0)
                max_pages = int((info or {}).get("max_pages") or 0)
                progress_percent = (info or {}).get("percent")
                if progress_percent is None:
                    if phase in {"starting", "fetching", "page_complete", "exhausted"}:
                        progress_percent = min(20, 2 + int(18 * pages_read / max(1, max_pages)))
                    elif phase.startswith("filter"):
                        progress_percent = 24
                    elif phase.startswith("quick"):
                        progress_percent = 45
                    elif phase.startswith("full"):
                        progress_percent = 75
                    elif phase == "ranking":
                        progress_percent = 97
                    elif phase == "complete":
                        progress_percent = 100
                    else:
                        progress_percent = 1
                progress_percent = max(0, min(100, int(progress_percent)))
                done = int((info or {}).get("done") or 0)
                total = int((info or {}).get("total") or 0)
                if phase in {"starting", "fetching", "page_complete", "exhausted"}:
                    progress_text = f"{progress_percent}% · {found} annonser hittade"
                elif phase.startswith("filter"):
                    progress_text = f"{progress_percent}% · Filtrerar kort" + (f" · {done}/{total}" if total else "")
                elif phase.startswith("quick"):
                    progress_text = f"{progress_percent}% · Prioriterar" + (f" · {done}/{total}" if total else "")
                elif phase.startswith("full"):
                    progress_text = f"{progress_percent}% · Analyserar toppkandidater" + (f" · {done}/{total}" if total else "")
                elif phase == "ranking":
                    progress_text = f"{progress_percent}% · Rankar Top 5"
                elif phase == "complete":
                    progress_text = "100% · Klart"
                else:
                    progress_text = f"{progress_percent}% · Bearbetar…"
                seller_progress_bar.progress(progress_percent, text=progress_text)
                if phase == "fetching":
                    seller_progress_line.caption(f"Sida {page} · {found} annonser")
                elif phase == "page_complete":
                    seller_progress_line.caption(f"Sida {page} klar · {found} annonser")
                elif phase == "exhausted":
                    seller_progress_line.caption(f"Alla sidor lästa · {found} annonser")
                elif phase == "complete":
                    seller_progress_line.caption(f"{found} annonser · rankar bästa korten")

            try:
                try:
                    top5 = resolve_seller_top5(
                        alias,
                        local_market,
                        analyze_fn=_cached_seller_analysis,
                        sport=sport_key,
                        credentials=creds,
                        profile_url=seller_top5_profile_url_resolved,
                        progress_callback=_seller_search_progress,
                        quick_limit=60,
                        full_limit=8,
                        database_url=DATABASE_URL,
                        resume_checkpoint=_seller_previous_result.get("public_checkpoint"),
                    )
                except TypeError as exc:
                    # Streamlit may hot-reload app.py while keeping an older imported
                    # controller module in memory. Refresh that module automatically and
                    # continue the same user action instead of asking for another click.
                    if not any(name in str(exc) for name in ("profile_url", "progress_callback", "database_url")):
                        raise
                    seller_progress_bar.progress(2, text="2% · Synkar analysmotorn automatiskt…")
                    seller_progress_line.info("Ny kod upptäcktes · laddar om Seller Top 5-motorn utan att avbryta sökningen")
                    import importlib
                    import src.seller_top5_controller as _seller_top5_controller
                    _seller_top5_controller = importlib.reload(_seller_top5_controller)
                    top5 = _seller_top5_controller.resolve_seller_top5(
                        alias,
                        local_market,
                        analyze_fn=_cached_seller_analysis,
                        sport="all",
                        credentials=creds,
                        profile_url=seller_top5_profile_url_resolved,
                        progress_callback=_seller_search_progress,
                        quick_limit=60,
                        full_limit=8,
                        database_url=DATABASE_URL,
                        resume_checkpoint=_seller_previous_result.get("public_checkpoint"),
                    )
                if seller_top5_profile_url_resolved and top5.get("inventory_source") == "LOCAL_MARKET":
                    top5 = dict(top5)
                    top5["status"] = "PROFILE_INCOMPLETE"
                    top5["rows"] = []
                st.session_state["seller_top5_result"] = top5
                found_count = int(top5.get("inventory_count") or 0)
                quick_count = int(top5.get("quick_analysed") or 0)
                full_count = int(top5.get("full_analysed") or 0)
                source = top5.get("inventory_source") or "okänd källa"
                result_status = str(top5.get("status") or "")
                if result_status == "INVENTORY_PARTIAL":
                    pages_read = int(top5.get("public_pages_read") or 0)
                    next_page = int(top5.get("public_next_page") or 1)
                    seller_progress_bar.progress(100, text=f"{found_count} annonser inlästa · block klart")
                    seller_status.write(f"{pages_read} profilsidor lästa totalt · {found_count} annonser sparade · nästa block börjar på sida {next_page}.")
                    seller_status.update(label=f"📥 Block sparat för {alias} · fortsätt till nästa sida", state="complete", expanded=False)
                    st.rerun()  # refresh Seller Top 5 continuation UI
                elif result_status == "PROFILE_INCOMPLETE":
                    seller_progress_bar.progress(0, text="Profilinläsningen behöver fortsätta · tryck på Läs nästa sida")
                    seller_status.update(label=f"⚠️ Hela profilen för {alias} är inte inläst", state="error", expanded=True)
                    st.rerun()  # refresh continuation button after incomplete profile
                else:
                    seller_status.write(
                        f"{found_count} annonser hittade · {quick_count} snabbanalyserade · "
                        f"{full_count} fullanalyserade · källa: {source}."
                    )
                    seller_progress_bar.progress(100, text="100% · Klart")
                    seller_status.update(label=f"✅ Sökning klar för {alias}", state="complete", expanded=False)
            except Exception:
                try:
                    seller_progress_bar.progress(0, text="Sökningen avbröts")
                except Exception:
                    pass
                seller_status.update(label=f"❌ Sökningen av {alias} avbröts", state="error", expanded=True)
                raise

    if seller_top5_alias or seller_top5_profile_url or _seller_previous_result:
        st.button(
            "Rensa säljsökningen",
            key="seller_top5_clear",
            use_container_width=True,
            on_click=_clear_seller_top5_ui,
            help="Tar bort säljarens resultat och fortsättningsläge. Den vanliga fyndsökningen påverkas inte.",
        )



    seller_top5_result = st.session_state.get("seller_top5_result")
    _seller_result_status = str((seller_top5_result or {}).get("status") or "")
    if seller_top5_result and _seller_result_status == "INVENTORY_PARTIAL":
        _saved = int(seller_top5_result.get("inventory_count") or 0)
        _pages = int(seller_top5_result.get("public_pages_read") or 0)
        _next = int(seller_top5_result.get("public_next_page") or 1)
        _total_est = seller_top5_result.get("total_listing_estimate")
        _remaining_est = seller_top5_result.get("remaining_listing_estimate")
        if _total_est:
            _inventory_line = f"{_saved} inlästa · cirka {int(_remaining_est or 0)} kvar · {_pages} sidor lästa"
        else:
            _inventory_line = f"{_saved} inlästa · {_pages} sidor lästa · fortsätter från sida {_next}"
        if seller_top5_result.get("resume_required"):
            st.warning(f"Sökningen pausades av ett hämtningsfel · {_inventory_line}. Tryck på **Fortsätt söka** för att försöka samma sida igen.")
        else:
            st.info(f"Delstopp efter tre profilsidor · {_inventory_line}. Tryck på **Fortsätt söka** ovan; sökningen fortsätter från sida {_next} utan att börja om.")
    elif seller_top5_result and _seller_result_status == "PROFILE_INCOMPLETE":
        st.caption("Profilen är inte färdigläst ännu. Fortsätt med knappen ovan.")
    if seller_top5_result and not (seller_top5_result.get("rows") or []):
        _public_status = str(seller_top5_result.get("public_status") or "")
        _public_error = str(seller_top5_result.get("public_error") or "").strip()
        if _public_status and _public_status != "OK":
            st.error(f"Kunde inte läsa annonser från Tradera-profilen ({_public_status}).")
            if _public_error:
                st.caption(_public_error)
            st.caption("Ingen Top 5 visas förrän minst en riktig annons har lästs in.")
        elif _seller_result_status not in {"PROFILE_INCOMPLETE", "INVENTORY_PARTIAL"}:
            st.warning("Sökningen gav ännu inga läsbara kortannonser. Försök igen; FlipFynd visar inte en tom körning som ett lyckat resultat.")
    if (
        seller_top5_result
        and _seller_result_status != "PROFILE_INCOMPLETE"
        and int(seller_top5_result.get("inventory_count") or 0) > 0
    ):
        seller_name = seller_top5_result.get("seller") or str(seller_top5_alias or "").strip()
        inv_count = int(seller_top5_result.get("inventory_count") or 0)
        _ranked_rows = seller_top5_result.get("rows") or []
        _find_rows = [row for row in _ranked_rows if seller_result_tier(row) == "FIND"]
        _research_rows = [row for row in _ranked_rows if seller_result_tier(row) == "RESEARCH"]
        _seller_display_rows = (_find_rows + _research_rows)[:5]
        if _find_rows and _seller_result_status == "INVENTORY_PARTIAL":
            st.markdown(f"### 🏆 Verifierade fynd just nu · {seller_name}")
            st.caption("Preliminär lista · uppdateras när fler annonser hittas.")
        elif _find_rows:
            st.markdown(f"### 🏆 Verifierade fynd · {seller_name}")
        elif _research_rows:
            st.markdown(f"### 🔎 Kandidater värda fortsatt kontroll · {seller_name}")
            st.caption("Inga verifierade fynd ännu. Dessa kort har kortspecifika signaler men är inte köpklara.")
        else:
            st.markdown(f"### Inga starka fynd hittade ännu · {seller_name}")
            st.caption("FlipFynd visar inte vanliga bas- och standardkort som utfyllnad.")
        st.caption(
            f"{inv_count} annonser hittade · "
            f"{int(seller_top5_result.get('full_analysed') or 0)} djupanalyserade"
        )
        inventory_source = seller_top5_result.get("inventory_source")
        if inventory_source == "TRADERA_API":
            st.caption("Live via Tradera")
        elif inventory_source == "TRADERA_PUBLIC_PROFILE":
            pages_read = int(seller_top5_result.get("public_pages_read") or 0)
            st.caption(f"Tradera-profil · {pages_read} sidor lästa")
            if seller_top5_result.get("public_inventory_complete"):
                st.caption("✅ Hela säljarprofilen är inläst.")
        elif inventory_source == "LOCAL_MARKET":
            reason = seller_top5_result.get("fallback_reason")
            if reason == "NO_API_CREDENTIALS":
                st.caption("Källa: redan inläst FlipFynd-data · Tradera API är inte konfigurerat.")
            elif reason == "API_FAILED":
                api_status = seller_top5_result.get("api_status") or "okänt fel"
                st.caption(f"Källa: redan inläst FlipFynd-data · API-fallback efter {api_status}.")
            else:
                st.caption("Källa: redan inläst FlipFynd-data.")
        rows = _seller_display_rows
        rejected_count = int(seller_top5_result.get("domain_rejected_count") or 0)
        card_count = int(seller_top5_result.get("card_inventory_count") or 0)
        if rejected_count:
            st.caption(f"{rejected_count} tydliga icke-kortannonser filtrerades bort. {card_count} kortkandidater återstod.")
        if seller_top5_result.get("ranking_source") == "ORDINARY_FLIPFYND_RANK":
            st.caption("Slutlig ranking använder samma analysmotor som ordinarie FlipFynd-sökningen.")
        if not rows:
            st.info("Inget kort klarade kvalitetsgränsen ännu. Top 5 uppdateras när fler sidor läses.")
        elif len(rows) < 5:
            st.caption(f"Topplistan innehåller {len(rows)} kort eftersom färre än fem giltiga, unika kortannonser kunde läsas.")
        _find_rank = 0
        _research_rank = 0
        _research_heading_shown = False
        for row in rows[:5]:
            title = row.get("title") or "Kortannons"
            price = row.get("price")
            decision = str(row.get("decision") or "SKIP").upper()
            _row_tier = seller_result_tier(row)
            # Reuse the final tier already computed above. A new named import
            # can crash a hot deployment with an older loaded seller module.
            if _row_tier == "FIND":
                badge = "🟢 KÖP"
            elif (row.get("asking_price_opportunity") or {}).get("possible_find"):
                badge = "🟡 Möjligt fynd · begärda priser"
            elif decision.startswith(("KÖP", "UNDERSÖK")):
                badge = "🟡 Värt att undersöka"
            else:
                badge = "⚪ Kandidat · ej verifierad"
            if _row_tier == "FIND":
                _find_rank += 1
                _position_label = f"Fynd #{_find_rank}"
            else:
                _research_rank += 1
                _position_label = f"Research #{_research_rank}"
                if _find_rows and not _research_heading_shown:
                    st.markdown("### 🔎 Researchkandidater – inte fynd")
                    st.caption("Kortspecifika signaler gör dem värda kontroll, men ekonomin är inte verifierad.")
                    _research_heading_shown = True
            st.markdown(f"#### {_position_label} · {title}")
            _rank_score = float(row.get("rank_score") or 0)
            if price is not None:
                try:
                    st.markdown(f"**{float(price):.0f} kr** · {badge}")
                except (TypeError, ValueError):
                    st.markdown(badge)
            else:
                st.markdown(badge)
            render_asking_price_opportunity(row.get("asking_price_opportunity"))
            _opportunity_score = float(row.get("seller_opportunity_score") or _rank_score)
            st.caption(f"Granskningsprioritet {_opportunity_score:.0f}/100")
            _signal_labels = {
                "one_of_one": "1/1",
                "serial_numbered": "Numrerat",
                "autograph": "Autograf",
                "patch_relic": "Patch/relic",
                "case_hit_ssp": "SSP/case hit",
                "premium_insert": "Premiuminsert",
                "rookie": "Rookie",
                "premium_parallel": "Premium parallel",
                "error_variation": "Variation/feltryck",
                "short_print": "Short print",
                "football_named_chase": "Checklistad fotbolls-chase",
                "flagship_rookie_variant": "Young Guns-variant",
                "upper_deck_day_with_cup": "Day With The Cup",
                "upper_deck_population_count": "Population Count",
                "upper_deck_program_of_excellence": "Program of Excellence",
                "named_chase_insert": "Checklistad chase-insert",
                "elite_parallel": "Extrem parallel",
                "premium_autograph_structure": "Premiumautografstruktur",
                "premium_relic_structure": "Premium patch/relic-struktur",
                "premium_issue_variant": "Premiumutgåva/variant",
            }
            _signals = [
                _signal_labels.get(signal, str(signal))
                for signal in (row.get("collector_signals") or [])
                if signal
            ]
            if _signals:
                st.caption("Varför den prioriteras: " + " · ".join(_signals))
            if _row_tier != "FIND":
                st.caption("Prioriterad för kontroll – inte en köpsignal.")
            reason = str(row.get("reason") or "").strip()
            if reason:
                st.caption(reason)
            with st.expander("Analysdetaljer", expanded=False):
                st.caption(
                    f"Spelare {float(row.get('player_market_score') or 0):.0f}/100 · "
                    f"Market edge {float(row.get('market_edge') or 0):.0f}/100 · "
                    f"Värderingssäkerhet {float(row.get('valuation_confidence') or 0):.0f}/100"
                )
                st.caption(
                    f"Exact SOLD {int(row.get('sold_comps') or 0)} · "
                    f"riskjusterad vinst {float(row.get('risk_adjusted_profit') or 0):.0f} kr"
                )
                _ebay = row.get("ebay_active_context") or {}
                if _ebay.get("ok"):
                    _median = _ebay.get("median_usd")
                    _range = ""
                    if _ebay.get("min_usd") is not None and _ebay.get("max_usd") is not None:
                        _range = f" · spann ${_ebay['min_usd']:.2f}–${_ebay['max_usd']:.2f}"
                    st.caption(
                        f"eBay aktiva annonser: {int(_ebay.get('listing_count') or 0)} identitetsmatchade av "
                        f"{int(_ebay.get('raw_listing_count') or 0)} träffar"
                        + (f" · median ${_median:.2f}" if _median is not None else "")
                        + _range
                    )
                    st.caption("Begärda priser kan ge möjliga fynd. De visar inte vad korten har sålts för.")
                _readiness = row.get("deal_readiness") or {}
                if _readiness.get("blockers"):
                    st.caption("Inte köpklar: " + " · ".join(_readiness["blockers"][:3]))
            if row.get("analysis_level") == "quick_fallback":
                st.caption("Preliminär analys – djupanalys återstår.")
            elif row.get("seller_deep_route") == "HIDDEN_FIND_EXPLORATION":
                st.caption("Dolt fynd-urval: annonsen djupanalyserades trots svag rubrik. Detta är inte i sig en köpsignal.")
            if row.get("url"):
                st.link_button("Öppna annonsen ↗", row.get("url"), use_container_width=True)
            st.divider()
        for empty_rank in range(len(rows) + 1, 6):
            st.caption(f"#{empty_rank} — Ingen kandidat klarade kvalitetsgränsen ännu")
