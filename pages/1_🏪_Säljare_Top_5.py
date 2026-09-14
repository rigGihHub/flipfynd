import os
from pathlib import Path

import streamlit as st

from src.analyzer import analyze_item
from src.loader import load_data
from src.seller_identity import seller_alias
from src.seller_top5 import build_seller_top5
from src.tradera_seller_inventory import discover_active_seller_inventory


st.set_page_config(page_title="Säljare – Top 5 fynd", page_icon="🏪", layout="wide")

BASE_DIR = Path(__file__).resolve().parent.parent
LOCAL_MARKET_PATHS = [
    BASE_DIR / "tradera_data.json",
    BASE_DIR / "data" / "search_expansion_items.json",
]


def _resolve_tradera_api_credentials():
    app_id = os.getenv("TRADERA_APP_ID")
    app_key = os.getenv("TRADERA_APP_KEY")
    try:
        app_id = app_id or st.secrets.get("TRADERA_APP_ID")
        app_key = app_key or st.secrets.get("TRADERA_APP_KEY")
    except Exception:
        pass
    app_id = str(app_id or "").strip()
    app_key = str(app_key or "").strip()
    return (app_id, app_key) if app_id and app_key else None


def _dedupe(items):
    out = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        key = (
            item.get("tradera_item_id")
            or item.get("item_id")
            or item.get("id")
            or item.get("lank")
            or item.get("url")
            or item.get("link")
        )
        if key:
            out[str(key)] = item
    return list(out.values())


def _local_seller_inventory(alias):
    wanted = str(alias or "").strip().casefold()
    if not wanted:
        return []
    rows = []
    for path in LOCAL_MARKET_PATHS:
        rows.extend(load_data(str(path)))
    matches = []
    for row in rows:
        current = seller_alias(row)
        if current and current.casefold() == wanted:
            matches.append(row)
    return _dedupe(matches)


def _fetch_seller_inventory(alias):
    """Prefer Tradera API, then fall back to already-loaded FlipFynd market data."""
    creds = _resolve_tradera_api_credentials()
    if creds:
        fetched = discover_active_seller_inventory(
            seller_alias=alias,
            app_id=creds[0],
            app_key=creds[1],
            category_id=0,
        )
        if fetched.get("ok") and fetched.get("items"):
            fetched["source"] = "tradera_api"
            return fetched

    local_items = _local_seller_inventory(alias)
    if local_items:
        return {
            "ok": True,
            "status": "LOCAL_FALLBACK",
            "items": local_items,
            "seller": {"alias": alias},
            "source": "flipfynd_loaded_market",
        }

    return {
        "ok": False,
        "status": "NO_SELLER_DATA",
        "items": [],
        "seller": {"alias": alias},
        "source": "none",
    }


st.title("🏪 Fynd hos en säljare")
st.caption(
    "Skriv ett Tradera-säljarnamn. FlipFynd försöker först hämta säljarens aktiva annonser via Tradera och använder annars redan inläst FlipFynd-data som fallback."
)

alias = st.text_input("Säljarnamn på Tradera", placeholder="t.ex. Etanol71")
sport_label = st.radio("Sport", ["Hockey", "Fotboll"], horizontal=True)

if st.button("🔎 Hitta säljarens 5 bästa fynd", type="primary", use_container_width=True):
    seller_alias_input = str(alias or "").strip()
    if not seller_alias_input:
        st.warning("Ange ett säljarnamn först.")
    else:
        with st.spinner(f"Hämtar och analyserar annonser från {seller_alias_input}…"):
            fetched = _fetch_seller_inventory(seller_alias_input)
            if not fetched.get("ok"):
                st.session_state.pop("seller_top5_page_result", None)
                st.error(
                    "Jag hittar inga annonser för den säljaren i den data FlipFynd har tillgång till just nu. "
                    "Det kan betyda att Tradera-API saknas och att säljarens annonser ännu inte finns i den lokalt inlästa marknadsdatan."
                )
                st.caption(f"Status: {fetched.get('status')}")
            else:
                items = fetched.get("items") or []
                resolved = fetched.get("seller") or {}
                resolved_alias = resolved.get("alias") or seller_alias_input
                sport = "hockey" if sport_label == "Hockey" else "fotboll"
                result = build_seller_top5(
                    resolved_alias,
                    items,
                    analyze_fn=analyze_item,
                    sport=sport,
                    quick_limit=max(60, len(items)),
                    full_limit=10,
                )
                result["inventory_source"] = fetched.get("source")
                st.session_state["seller_top5_page_result"] = result

result = st.session_state.get("seller_top5_page_result")
if result:
    seller = result.get("seller") or str(alias or "").strip()
    inventory_count = int(result.get("inventory_count") or 0)
    quick_count = int(result.get("quick_analysed") or 0)
    full_count = int(result.get("full_analysed") or 0)
    source = result.get("inventory_source")

    st.subheader(f"🏆 Top 5 hos {seller}")
    source_text = "Tradera API" if source == "tradera_api" else "redan inläst FlipFynd-data"
    st.caption(
        f"Källa: {source_text} · {inventory_count} annonser hittades · "
        f"{quick_count}/{inventory_count if inventory_count else quick_count} granskade · "
        f"{full_count} fullanalyserade"
    )

    if source != "tradera_api":
        st.info(
            "Fallback-läge: listan bygger på den marknadsdata som FlipFynd redan har läst in. "
            "Den kan därför missa annonser som ännu inte finns i den lokala datan."
        )

    rows = result.get("rows") or []
    if not rows:
        st.info("Inga tillräckligt analyserbara kandidater hittades hos säljaren just nu.")

    for idx, row in enumerate(rows[:5], start=1):
        with st.container(border=True):
            title = row.get("title") or "Kortannons"
            price = row.get("price")
            decision = str(row.get("decision") or "UNDERSÖK")
            label = row.get("label") or "BEHÖVER VERIFIERAS"

            st.markdown(f"### #{idx} {title}")
            facts = []
            if price is not None:
                try:
                    facts.append(f"{float(price):.0f} kr")
                except (TypeError, ValueError):
                    pass
            facts.extend([decision, label])
            st.caption(" · ".join(facts))

            sold = int(row.get("sold_comps") or 0)
            edge = float(row.get("market_edge") or 0)
            st.caption(f"Exact SOLD: {sold} · Market edge: {edge:.0f}/100")

            if row.get("reason"):
                st.write(row.get("reason"))

            if row.get("url"):
                st.link_button("Öppna annonsen ↗", row.get("url"), use_container_width=True)

st.caption(
    "Topplistan använder samma försiktiga evidensregler som FlipFynd. Saknas verifierade SOLD eller säker värdering visas kandidaten som UNDERSÖK i stället för KÖP."
)
