import os

import streamlit as st

from src.analyzer import analyze_item
from src.seller_top5 import build_seller_top5
from src.tradera_seller_inventory import discover_active_seller_inventory


st.set_page_config(page_title="Säljare – Top 5 fynd", page_icon="🏪", layout="wide")


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


st.title("🏪 Fynd hos en säljare")
st.caption("Skriv ett Tradera-säljarnamn. FlipFynd går igenom säljarens aktiva annonser och visar de fem bästa möjligheterna.")

alias = st.text_input("Säljarnamn på Tradera", placeholder="t.ex. Etanol71")
sport_label = st.radio("Sport", ["Hockey", "Fotboll"], horizontal=True)

if st.button("🔎 Hitta säljarens 5 bästa fynd", type="primary", use_container_width=True):
    seller_alias = str(alias or "").strip()
    if not seller_alias:
        st.warning("Ange ett säljarnamn först.")
    else:
        creds = _resolve_tradera_api_credentials()
        if not creds:
            st.error("Tradera API är inte konfigurerat, så säljarens aktiva annonser kan inte hämtas automatiskt ännu.")
        else:
            with st.spinner(f"Hämtar och analyserar aktiva annonser från {seller_alias}…"):
                fetched = discover_active_seller_inventory(
                    seller_alias=seller_alias,
                    app_id=creds[0],
                    app_key=creds[1],
                    category_id=0,
                )
                if not fetched.get("ok"):
                    st.session_state.pop("seller_top5_page_result", None)
                    st.error("Kunde inte hämta säljarens aktiva annonser från Tradera.")
                    if fetched.get("status"):
                        st.caption(f"Status: {fetched.get('status')}")
                else:
                    items = fetched.get("items") or []
                    resolved = fetched.get("seller") or {}
                    resolved_alias = resolved.get("alias") or seller_alias
                    sport = "hockey" if sport_label == "Hockey" else "fotboll"
                    result = build_seller_top5(
                        resolved_alias,
                        items,
                        analyze_fn=analyze_item,
                        sport=sport,
                        quick_limit=max(60, len(items)),
                        full_limit=10,
                    )
                    st.session_state["seller_top5_page_result"] = result

result = st.session_state.get("seller_top5_page_result")
if result:
    seller = result.get("seller") or str(alias or "").strip()
    inventory_count = int(result.get("inventory_count") or 0)
    quick_count = int(result.get("quick_analysed") or 0)
    full_count = int(result.get("full_analysed") or 0)

    st.subheader(f"🏆 Top 5 hos {seller}")
    st.caption(
        f"{inventory_count} aktiva annonser hittades · "
        f"{quick_count}/{inventory_count if inventory_count else quick_count} granskade · "
        f"{full_count} fullanalyserade"
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

st.caption("Topplistan använder samma försiktiga evidensregler som FlipFynd. Saknas verifierade SOLD eller säker värdering visas kandidaten som UNDERSÖK i stället för KÖP.")
