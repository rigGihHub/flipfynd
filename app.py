Warning: truncated output (original token count: 98127)
Total output lines: 6733

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
try:
    from src.persistent_search_jobs import (
        available as jobs_available, create_job, latest_active_job, latest_completed_job, latest_job,
        ensure_seller_inventory_job, seller_inventory_job_status,
    )
except ImportError:
    # Streamlit Cloud can briefly run app.py with an older cached imported
    # module during rolling deploys. Keep the whole app alive; latest_job is
    # optional until the module catches up.
    from src.persistent_search_jobs import available as jobs_available, create_job, latest_active_job, latest_completed_job
    latest_job = lambda **kwargs: None
    ensure_seller_inventory_job = lambda **kwargs: None
    seller_inventory_job_status = lambda **kwargs: None
from src.ordinary_search_job_contract import build_ordinary_search_job_payload, unpack_completed_ordinary_job
from src.persistent_store import load_namespace as load_persistent_namespace, save_namespace as save_persistent_namespace
from src.latest_market import LATEST_MAX_PAGES, latest_analysis_items
from src.seller_live_full_analysis import full_analyze_live_seller_item
from src.seller_top5 import build_seller_top5, seller_result_tier, seller_has_positive_purchase_price
from src.asking_price_ui import render_asking_price_opportunity, render_asking_price_shortlist
from src.seller_profit_display import (
    build_seller_net_profit_summary,
    known_negative_net_profit,
    known_positive_net_profit,
)
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

# Visible runtime marker. This makes deploy/hot-reload state observable instead
# of guessing from stale search results.
RUNTIME_BUILD = "2026-09-20.63-decode-tradera-markup"
# A tiny source change at module startup intentionally forces Streamlit Cloud
# to restart/reload app.py instead of relying on hot-reloaded imported modules.

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



APP_VERSION = "v0.14.65"
SELLER_PRESENTATION_CONTRACT = "positive-price-positive-known-profit-v3"


def _seller_ui_row_is_safe(row):
    """Fail closed before seller cards are rendered by this app process.

    Streamlit can hot-reload app.py while retaining imported modules. Keep the
    final money-safety check local so cached analyser code cannot bypass it.
    """
    if not isinstance(row, dict):
        return False

    source = row.get("source_item") if isinstance(row.get("source_item"), dict) else {}
    price_keys = ("price", "pris", "current_price")
    price_container = row if any(key in row for key in price_keys) else source
    positive_price = False
    for key in price_keys:
        value = price_container.get(key)
        if value in (None, "") or isinstance(value, bool):
            continue
        try:
            positive_price = float(value) > 0
        except (TypeError, ValueError):
            continue
        break
    if not positive_price:
        return False

    asking = row.get("asking_price_opportunity")
    if not isinstance(asking, dict):
        asking = {}
    margin_values = (asking.get("net_margin"), row.get("asking_net_margin"))
    if row.get("valuation_display_safe") is True or str(row.get("practical_price_source") or "").upper() == "VERIFIED":
        margin_values += (row.get("net_profit_estimate"), row.get("estimated_net_profit"))
    for value in margin_values:
        if value in (None, "") or isinstance(value, bool):
            continue
        try:
            if float(value) < 0:
                return False
        except (TypeError, ValueError):
            continue
    return True

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
    # Keep the last completed result visible while fresh listings load.
    # Mark it stale instead of blanking the user's screen; a new Hitta fynd run
    # will replace it against the updated dataset.
    st.session_state["result_cache"] = {}
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
        # Fresh market data makes the old analysis stale, not disposable.
        # Keep it visible until the replacement analysis completes.
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
        mode=f"seller_v7_verified_profit_gate_{sport}_{strategy_mode}",
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
            restored_signature = str(restored.get("signature") or "")
            # Never restore a completed search produced by an older analysis
            # engine. This was keeping obsolete Top 5 rows visible even after
            # the ranking/price pipeline changed.
            # Restore the last completed search across browser/session loss.
            # Exact engine-version freshness is handled by the next explicit
            # Hitta fynd run; losing the user's visible results is worse than
            # showing them with a clear restored marker.
            if restored_signature:
                st.session_state["results"] = restored.get("results") or []
                st.session_state["debug"] = restored.get("debug") if isinstance(restored.get("debug"), dict) else {}
                st.session_state["last_completed_search_signature"] = restored_signature
                st.session_state["results_data_version"] = restored.get("data_version") or get_data_version()
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
st.markdown(
    f'<div class="ff-status-strip">{APP_VERSION} &nbsp;•&nbsp; BUILD {RUNTIME_BUILD} &nbsp;•&nbsp; HOCKEY / FOTBOLL &nbsp;•&nbsp; TRADERA SCANNER</div>',
    unsafe_allow_html=True,
)

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
    # Preserve the last completed cards across refresh/navigation. They are
    # labelled stale until a new analysis completes instead of disappearing.
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
    "🔄 Uppdatera senaste annonser" if _has_data else "📥 Läs in senaste annonser",
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

    latest_selected = int(debug.get("latest_fast_selected", 0) or 0)
    archive_selected = int(debug.get("archive_fast_selected", 0) or 0)
    if debug.get("automatic_archive_coverage"):
        st.caption(
            f"Analysurval: {latest_selected} från senaste hämtningen + "
            f"{archive_selected} äldre sparade annonser. Äldre annonser får en reserverad chans utan att analysbudgeten ökas."
        )

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
        "Sökningen prioriterar senaste annonserna och reserverar automatiskt en del av analysen för äldre sparade annonser. "
        "Under Avancerade filter kan du låta hela arkivet konkurrera på samma villkor."
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
            help="Normalt prioriteras senaste annonserna och en begränsad del av äldre lagret granskas automatiskt. Slå på för ett bredare arkivurval.",
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
        ANALYSIS_ENGINE_VERSION = "ordinary-v2-archive-price-routing-20260925-33"
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
                data_version=f"{scoped_data_version}:{ANALYSIS_ENGINE_VERSION}",
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
                {"signature": current_run_signature, "results": results, "debug": debug, "data_version": get_data_version()},
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
            top_rows = [
                row for row in (opportunity_top5.get("rows") or [])
                if not known_negative_net_profit(row)
            ]
            rescued_count = sum(1 for row in top_rows if row.get("candidate_rescue"))

            current_debug = st.session_state.get("debug") or {}
            price_funnel = current_debug.get("price_research_funnel") or {}
            if not price_funnel:
                st.error("Prisfunneln saknas i analysresultatet. Debug-fält: " + (", ".join(sorted(current_debug.keys())) or "inga"))
            if price_funnel:
                with st.expander("💰 Prisresearch – felsökning", expanded=True):
                    ebay_ready = bool(current_debug.get("ebay_credentials_configured"))
                    st.write("eBay API: " + ("✅ konfigurerad" if ebay_ready else "❌ saknar EBAY_CLIENT_ID / EBAY_CLIENT_SECRET"))
                    st.write(
                        f"Sökbar identitet {price_funnel.get('searchable_identity', 0)} → "
                        f"routade {price_funnel.get('routed', 0)} "
                        f"(extra prispass {current_debug.get('adaptive_price_research_added', 0)}) → "
                        f"djupanalyserade {price_funnel.get('deep_analysed', 0)} → "
                        f"eBay-context {price_funnel.get('context_attached', 0)} → "
                        f"prisbedömning {price_funnel.get('opportunity_attached', 0)} → "
                        f"användbart jämförpris {price_funnel.get('usable_reference', 0)} → "
                        f"möjliga fynd {price_funnel.get('possible_find', 0)}"
                    )
                    statuses = (st.session_state.get("debug") or {}).get("price_research_status_counts") or {}
                    if statuses:
                        st.caption("Prisstatus: " + " · ".join(f"{k}: {v}" for k, v in sorted(statuses.items())))
                    target = int(current_debug.get("mispricing_sweep_target") or 0)
                    eligible = int(price_funnel.get("searchable_identity") or 0)
                    usable = int(price_funnel.get("usable_reference") or 0)
                    finds = int(price_funnel.get("possible_find") or 0)
                    if eligible:
                        st.caption(
                            f"Fyndsvep: målet är att prisundersöka upp till {target or eligible} av {eligible} "
                            f"sökbara kort. {usable} fick användbart jämförpris och {finds} gav positiv fyndmarginal."
                        )

            actual_find_count = sum(
                1 for row in top_rows
                if (
                    (row.get("decision") == "KÖP")
                    or (row.get("asking_positive") is True)
                    or (
                        row.get("practical_margin") is not None
                        and float(row.get("practical_margin") or 0) > 0
                        and row.get("practical_price_source") in {"VERIFIED", "ACTIVE_PRICE"}
                        and int(row.get("asking_comparison_count") or 0) >= 2
                    )
                )
            )
            if actual_find_count:
                st.markdown("### 🏆 Fynd att undersöka")
                st.caption(f"{actual_find_count} kandidat(er) har verklig positiv prisindikation i den här körningen. Övriga rader är bäst av resten.")
            else:
                st.markdown("### 🔎 Närmast fyndgränsen – inga fynd hittades")
                st.caption("FlipFynd hittade inget kort med tillräckligt stark positiv prisindikation. Listan visar de fem kandidater som ligger närmast en lönsam vidareförsäljning av det som kunde prisbedömas.")
            if rescued_count:
                st.caption(f"{rescued_count} kandidat(er) visas för vidare kontroll trots att positiv marginal inte är bevisad.")
            if not top_rows:
                st.warning(
                    "Inga kandidater med positiv eller ännu okänd fyndmarginal hittades i den analyserade gruppen. "
                    "FlipFynd visar inte längre kända minusaffärer bara för att fylla Top 5."
                )
            else:
                tier_labels = {
                    "VERIFIED": "Verifierat fynd",
                    "PROMISING": "Lovande · undersök",
                    "REMAINDER": "Inte fynd · bäst av resten",
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
                        "Nettovinst": (
                            f"{build_seller_net_profit_summary(row)['value']:+.0f} kr"
                            if build_seller_net_profit_summary(row)["available"]
                            else "Ej beräkningsbar"
                        ),
                        "Fyndpotential": f"{float(row.get('potential') or 0):.0f}/100",
                        "Säkerhet": f"{float(row.get('certainty') or 0):.0f}/100",
                    })
                st.dataframe(table_rows, use_container_width=True, hide_index=True)
                st.caption("Prisindikation används för fyndjakt. SOLD ger starkare bekräftelse när det finns, men krävs inte för UNDERSÖK.")
                for rank, row in enumerate(top_rows, start=1):
                    with st.expander(f"#{rank} · {row.get('title') or 'Okänt kort'}", expanded=False):
                        st.write(f"**{row.get('decision') or 'UNDERSÖK'}** · {tier_labels.get(row.get('tier'), 'Bäst av resten')}")
                        facts = []
                        if row.get("total_cost") is not None:
                            facts.append(f"total kostnad {float(row['total_cost']):.0f} kr")
  …48127 tokens truncated…nt']} utan tillräcklig såld-evidens • "
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
    if DATABASE_URL:
        try:
            save_persistent_namespace(DATABASE_URL, "seller_last_result", None)
        except Exception:
            pass
    try:
        for key in ("seller", "seller_profile"):
            if key in st.query_params:
                del st.query_params[key]
    except Exception:
        pass


if not st.session_state.get("seller_top5_result") and DATABASE_URL:
    try:
        _saved_seller = load_persistent_namespace(DATABASE_URL, "seller_last_result", {})
        if isinstance(_saved_seller, dict) and isinstance(_saved_seller.get("result"), dict):
            _saved_alias = str(_saved_seller.get("alias") or "").strip()
            _saved_profile = str(_saved_seller.get("profile_url") or "").strip()
            _saved_result = dict(_saved_seller["result"])
            # The compact seller_last_result may lag behind the per-seller
            # durable checkpoint. On a fresh browser session, merge the newer
            # checkpoint before restoring the UI so leaving for a Tradera ad
            # can never rewind thousands of already saved listings.
            try:
                _restore_alias = _saved_alias or str(_saved_result.get("seller") or "").strip()
                _restore_profile = _saved_profile
                if _restore_profile:
                    _restore_key = _seller_top5_controller._checkpoint_key(_restore_alias, _restore_profile)
                    _durable_cp = _seller_top5_controller.load_checkpoint(
                        _restore_key, session=st.session_state, database_url=DATABASE_URL
                    )
                    _saved_cp = _saved_result.get("public_checkpoint") or {}
                    if isinstance(_durable_cp, dict) and int(_durable_cp.get("next_page") or 0) > int(_saved_cp.get("next_page") or 0):
                        _saved_result["public_checkpoint"] = _durable_cp
                        _saved_result["public_next_page"] = int(_durable_cp.get("next_page") or 1)
                        _saved_result["public_pages_read"] = max(0, int(_durable_cp.get("next_page") or 1) - 1)
                        _saved_result["inventory_count"] = len(_durable_cp.get("items") or {})
                        _saved_result["total_listing_estimate"] = _durable_cp.get("total_listing_estimate")
            except Exception:
                pass
            if _saved_alias and not st.session_state.get("seller_top5_alias"):
                st.session_state["seller_top5_alias"] = _saved_alias
            if _saved_profile and not st.session_state.get("seller_top5_profile_url"):
                st.session_state["seller_top5_profile_url"] = _saved_profile
            st.session_state["seller_top5_result"] = _saved_result
    except Exception:
        pass

_seller_existing_result = st.session_state.get("seller_top5_result") or {}
# The durable namespace can lag one click behind the in-session crawl result.
# Prefer whichever checkpoint has progressed furthest so "Sök vidare" cannot
# regress from page 10 back to the older page-1/9 block.
try:
    _persisted_seller = load_persistent_namespace(DATABASE_URL, "seller_last_result", {}) if DATABASE_URL else {}
    _persisted_result = (_persisted_seller or {}).get("result") if isinstance(_persisted_seller, dict) else {}
    _session_next = int(((_seller_existing_result or {}).get("public_checkpoint") or {}).get("next_page") or 0)
    _persisted_next = int(((_persisted_result or {}).get("public_checkpoint") or {}).get("next_page") or 0)
    if isinstance(_persisted_result, dict) and _persisted_next > _session_next:
        _seller_existing_result = _persisted_result
        st.session_state["seller_top5_result"] = _persisted_result
except Exception:
    pass
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
    _seller_has_saved_inventory = int(_seller_previous_result.get("inventory_count") or 0) > 0
    if _seller_continue_inventory:
        _seller_button_label = "🔎 Sök vidare – läs nästa annonser"
    elif _seller_has_saved_inventory:
        _seller_button_label = "🔄 Sök igen – uppdatera säljaren"
    else:
        _seller_button_label = "🔎 Hitta säljarens bästa kort"
    if _seller_has_saved_inventory:
        st.caption(
            f"{int(_seller_previous_result.get('inventory_count') or 0)} annonser sparade hittills. "
            "Nästa sökning behåller dem och fortsätter/uppdaterar samma säljare."
        )
    if seller_top5_profile_url_resolved and jobs_available():
        try:
            _bg_job = seller_inventory_job_status(
                profile_url=seller_top5_profile_url_resolved,
                seller=str(seller_top5_alias or "").strip(),
            )
            if _bg_job:
                _bg_status = str(_bg_job.get("status") or "")
                _bg_result = _bg_job.get("result") or {}
                _bg_checkpoint = _bg_result.get("checkpoint") or {}
                _bg_saved = int(_bg_result.get("inventory_count") or len(_bg_checkpoint.get("items") or {}))
                _bg_next = int(_bg_checkpoint.get("next_page") or 1)
                if _bg_status in {"QUEUED", "RUNNING"}:
                    st.info(f"Bakgrundssökning pågår · {_bg_saved} unika annonser sparade · fortsätter från sida {_bg_next}")
                elif _bg_status == "COMPLETED":
                    st.success(f"Bakgrundsinläsning klar · {_bg_saved} unika annonser sparade")
                elif _bg_status == "FAILED":
                    st.warning("Bakgrundsinläsningen avbröts. Sparat checkpoint finns kvar och nästa körning kan fortsätta.")
        except Exception:
            pass
    if st.button(_seller_button_label, key="seller_top5_run", use_container_width=True):
        alias = str(seller_top5_alias or "").strip()
        if not alias and not seller_top5_profile_url_resolved:
            st.warning("Klistra in en Tradera-profillänk eller ange ett säljarnamn.")
        else:
            # Public seller profiles can be crawled by the persistent worker.
            # Queue that I/O-heavy part first so leaving the browser does not
            # cancel inventory discovery. Ranking remains on the existing path
            # until the headless analyser is fully separated.
            if seller_top5_profile_url_resolved and jobs_available():
                _resume_page = int(((_seller_previous_result.get("public_checkpoint") or {}).get("next_page")) or 1)
                _active = ensure_seller_inventory_job(
                    profile_url=seller_top5_profile_url_resolved,
                    seller=alias,
                    start_page=_resume_page,
                    max_pages=120,
                )
                if _active:
                    st.session_state["seller_background_job_id"] = _active.get("job_id")
                st.info("Säljarens annonser har lagts i bakgrundskön. Du kan lämna sidan utan att kön försvinner.")

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
                if phase in {"starting", "fetching", "fetch_retry", "page_complete", "exhausted"}:
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
                elif phase == "fetch_retry":
                    attempt = int((info or {}).get("attempt") or 1)
                    maximum = int((info or {}).get("max_attempts") or 3)
                    seller_progress_line.caption(
                        f"Tillfälligt hämtningsfel på sida {page} · försöker automatiskt igen {attempt}/{maximum}"
                    )
                elif phase == "page_complete":
                    seller_progress_line.caption(f"Sida {page} klar · {found} annonser")
                elif phase == "exhausted":
                    seller_progress_line.caption(f"Alla sidor lästa · {found} annonser")
                elif phase == "complete":
                    seller_progress_line.caption(f"{found} annonser · rankar bästa korten")

            try:
                try:
                    # Read continuation state at click-time. Streamlit reruns can
                    # make the earlier module-scope snapshot stale/empty.
                    _click_result = st.session_state.get("seller_top5_result") or {}
                    if not isinstance(_click_result, dict) or not (_click_result.get("public_checkpoint") or {}):
                        try:
                            _click_saved = load_persistent_namespace(DATABASE_URL, "seller_last_result", {}) if DATABASE_URL else {}
                            _click_persisted = (_click_saved or {}).get("result") if isinstance(_click_saved, dict) else {}
                            if isinstance(_click_persisted, dict):
                                _click_result = _click_persisted
                        except Exception:
                            pass
                    _visible_cp = (_click_result.get("public_checkpoint") or {}) if isinstance(_click_result, dict) else {}
                    # Streamlit can hot-reload app.py while retaining an older
                    # imported controller module. Reload it on each explicit
                    # seller-search click so continuation code matches GitHub.
                    import importlib as _seller_importlib
                    import src.seller_top5_controller as _seller_controller_live
                    _seller_controller_live = _seller_importlib.reload(_seller_controller_live)
                    _controller_start_debug = {
                        "source": "visible_result",
                        "next_page": int(_visible_cp.get("next_page") or 1),
                        "pages_read": int(_visible_cp.get("pages_read") or 0),
                        "items": len(_visible_cp.get("items") or {}),
                    }
                    st.session_state["seller_controller_start_debug"] = _controller_start_debug
                    top5 = _seller_controller_live.resolve_seller_top5(
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
                        # The visible result is the freshest checkpoint from
                        # the immediately preceding block. Pass it explicitly so
                        # continuation survives DB/session checkpoint lag.
                        resume_checkpoint=_visible_cp,
                        analysis_registry=(
                            (_click_result.get("analysis_registry") if isinstance(_click_result, dict) else None)
                            or (_visible_cp.get("analysis_registry") if isinstance(_visible_cp, dict) else None)
                            or {}
                        ),
                    )
                except TypeError as exc:
                    # Streamlit may hot-reload app.py while keeping an older imported
                    # controller module in memory. Refresh that module automatically and
                    # continue the same user action instead of asking for another click.
                    if not any(name in str(exc) for name in ("profile_url", "progress_callback", "database_url", "analysis_registry")):
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
                        analysis_registry=_seller_previous_result.get("analysis_registry") or {},
                    )
                if seller_top5_profile_url_resolved and top5.get("inventory_source") == "LOCAL_MARKET":
                    top5 = dict(top5)
                    top5["status"] = "PROFILE_INCOMPLETE"
                    top5["rows"] = []
                st.session_state["seller_top5_result"] = top5
                # Persist seller continuation/result independently of the
                # browser websocket so leaving the app cannot reset the crawl.
                if DATABASE_URL:
                    try:
                        save_persistent_namespace(
                            DATABASE_URL,
                            "seller_last_result",
                            {
                                "alias": alias,
                                "profile_url": seller_top5_profile_url_resolved,
                                "result": top5,
                            },
                        )
                    except Exception:
                        pass
                found_count = int(top5.get("inventory_count") or 0)
                quick_count = int(top5.get("quick_analysed") or 0)
                full_count = int(top5.get("full_unique_analysed") or top5.get("full_analysed") or 0)
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
        _diag_code = str(seller_top5_result.get("diagnostic_code") or "FF-SELLER-PARTIAL")
        if seller_top5_result.get("resume_required"):
            st.warning(f"Sökningen pausades av ett hämtningsfel · {_inventory_line}. Tryck på **Fortsätt söka** för att försöka samma sida igen.")
        else:
            st.info(f"Delstopp efter ett sökblock · {_inventory_line}. Tryck på **Fortsätt söka** ovan; sökningen fortsätter från sida {_next} utan att börja om.")
        _start_dbg = st.session_state.get("seller_controller_start_debug") or {}
        _diag_lines = [
            f"{_diag_code} | status={seller_top5_result.get('public_status')} | "
            f"saved={_saved} | pages={_pages} | next={_next} | "
            f"estimate={seller_top5_result.get('total_listing_estimate')} | "
            f"resume={bool(seller_top5_result.get('resume_required'))}"
        ]
        _coverage = seller_top5_result.get("analysis_coverage") or {}
        if _coverage:
            _diag_lines.append(
                f"FF-ANALYSIS-COVERAGE | quick={int(_coverage.get('quick_unique') or 0)}/"
                f"{int(_coverage.get('inventory_unique') or 0)} | "
                f"full={int(_coverage.get('full_unique') or 0)}/"
                f"{int(_coverage.get('inventory_unique') or 0)} | "
                f"full_remaining={int(_coverage.get('full_remaining') or 0)}"
            )
        _funnel = seller_top5_result.get("analysis_funnel") or {}
        if _funnel:
            _diag_lines.append(
                f"FF-CANDIDATE-FUNNEL | cards={int(_funnel.get('card_inventory') or 0)} | "
                f"quick={int(_funnel.get('quick_success') or 0)} | "
                f"merit={int(_funnel.get('merit_eligible') or 0)} | "
                f"full={int(_funnel.get('full_success') or 0)} | "
                f"positive_net={int(_funnel.get('positive_net_current') or 0)} | "
                f"verified_find={int(_funnel.get('verified_find_current') or 0)}"
            )
        if _start_dbg:
            _diag_lines.append(
                f"FF-CONTROLLER-START | source={_start_dbg.get('source')} | "
                f"next={_start_dbg.get('next_page')} | pages={_start_dbg.get('pages_read')} | "
                f"items={_start_dbg.get('items')}"
            )
        _public_error = seller_top5_result.get("public_error")
        if _public_error:
            _diag_lines.append(f"FF-PUBLIC-ERROR | {_public_error}")
        st.code("\n".join(_diag_lines), language=None)
        st.caption("Felsökning – allt ligger i samma kopierbara ruta.")
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
        _safe_ranked_rows = [
            row for row in _ranked_rows
            if (
                _seller_ui_row_is_safe(row)
                and known_positive_net_profit(row)
                and seller_has_positive_purchase_price(row)
            )
        ]
        _find_rows = [row for row in _safe_ranked_rows if seller_result_tier(row) == "FIND"]
        _research_rows = [row for row in _safe_ranked_rows if seller_result_tier(row) == "RESEARCH"]
        _seller_display_rows = (_find_rows + _research_rows)[:5]
        if _find_rows and _seller_result_status == "INVENTORY_PARTIAL":
            st.markdown(f"### 🏆 Verifierade fynd just nu · {seller_name}")
            st.caption("Preliminär lista · uppdateras när fler annonser hittas.")
        elif _find_rows:
            st.markdown(f"### 🏆 Verifierade fynd · {seller_name}")
        elif _seller_display_rows:
            st.markdown(f"### 🔎 Kandidater värda fortsatt kontroll · {seller_name}")
            st.caption("Inga verifierade fynd ännu. Dessa kort har kortspecifika signaler men är inte köpklara.")
        else:
            st.markdown(f"### Inga verifierade fynd i analyserade delen ännu · {seller_name}")
            st.caption("FlipFynd visar inte minusaffärer, okänd nettovinst eller vanliga standardkort som utfyllnad.")
        _full_unique = int(seller_top5_result.get("full_unique_analysed") or seller_top5_result.get("full_analysed") or 0)
        _full_remaining = int(seller_top5_result.get("full_remaining") or 0)
        st.caption(
            f"{inv_count} annonser hittade · "
            f"{_full_unique} unika djupanalyserade · {_full_remaining} återstår"
        )
        _result_funnel = seller_top5_result.get("analysis_funnel") or {}
        if _result_funnel and _seller_result_status != "INVENTORY_PARTIAL":
            with st.expander("Analystäckning och diagnostik", expanded=False):
                st.code(
                    "\n".join([
                        f"FF-SELLER-ANALYSIS | version={APP_VERSION} | seller={seller_name}",
                        f"inventory={inv_count} | cards={int(_result_funnel.get('card_inventory') or 0)} | "
                        f"unique={int(_result_funnel.get('inventory_unique') or 0)}",
                        f"quick={int(_result_funnel.get('quick_success') or 0)} | "
                        f"merit={int(_result_funnel.get('merit_eligible') or 0)} | "
                        f"full={int(_result_funnel.get('full_success') or 0)}",
                        f"positive_net={int(_result_funnel.get('positive_net_current') or 0)} | "
                        f"verified_find={int(_result_funnel.get('verified_find_current') or 0)} | "
                        f"shown={len(_seller_display_rows)}",
                        f"full_unique={_full_unique} | full_remaining={_full_remaining} | "
                        f"coverage={float(_result_funnel.get('cumulative_full_coverage_pct') or 0):.1f}%",
                        "recall=not_measured_without_labelled_ground_truth",
                    ]),
                    language=None,
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
            if _full_remaining > 0:
                st.info("Inget verifierat fynd i den analyserade delen ännu. Fortsatt sökning roterar vidare till tidigare oanalyserade annonser.")
            else:
                st.info("Hela det sparade kortlagret är analyserat och inget kort klarade den positiva nettovinst- och evidensgränsen.")
        elif len(rows) < 5:
            st.caption(
                f"Topplistan innehåller {len(rows)} kort eftersom bara {len(rows)} "
                "klarade pris-, kvalitets- och evidensgränsen hittills."
            )
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
            try:
                if price is not None and float(price) > 0:
                    st.markdown(f"**{float(price):.0f} kr** · {badge}")
                else:
                    st.markdown(badge)
            except (TypeError, ValueError):
                st.markdown(badge)
            _profit = build_seller_net_profit_summary(row)
            if _profit["available"]:
                st.markdown(
                    f"**{_profit['label']}: {_profit['value']:+.0f} kr** · "
                    f"{_profit['basis']}"
                )
            else:
                st.markdown("**Nettovinst: ej beräkningsbar**")
                st.caption(_profit["basis"].capitalize() + ".")
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
                _ad_url = str(row.get("url") or "").replace('"', "%22")
                st.markdown(
                    f'<a href="{_ad_url}" target="_blank" rel="noopener noreferrer" '
                    f'style="display:block;text-align:center;padding:.55rem .75rem;'
                    f'border:1px solid rgba(128,128,128,.45);border-radius:.5rem;'
                    f'text-decoration:none;font-weight:600;">Öppna annonsen ↗</a>',
                    unsafe_allow_html=True,
                )
            st.divider()
        for empty_rank in range(len(rows) + 1, 6):
            st.caption(f"#{empty_rank} — Ingen kandidat klarade kvalitetsgränsen ännu")
