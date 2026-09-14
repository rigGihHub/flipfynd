from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

import_old = "from src.seller_top5_controller import resolve_seller_top5\n"
import_new = (
    "from src.seller_top5_controller import resolve_seller_top5\n"
    "from src.seller_inventory_triage import build_seller_inventory_triage\n"
)
if "from src.seller_inventory_triage import build_seller_inventory_triage" not in text:
    if import_old not in text:
        raise SystemExit("seller triage import anchor missing")
    text = text.replace(import_old, import_new, 1)

# Add automatic triage after each successful save. There are two import branches.
needle = '''                        get_data.clear()\n                        st.session_state["result_cache"] = {}\n                        st.session_state["seller_inventory_import_status"] = {'''
replacement = '''                        get_data.clear()\n                        st.session_state["result_cache"] = {}\n                        triage_market = get_data(get_data_version())\n                        triage_sport = "hockey" if seller_top5_sport_label == "Hockey" else "football"\n                        st.session_state["seller_inventory_triage_result"] = build_seller_inventory_triage(\n                            import_alias,\n                            triage_market,\n                            analyze_fn=analyze_item,\n                            sport=triage_sport,\n                            max_fast_analyses=120,\n                            top_n=20,\n                        )\n                        st.session_state["seller_inventory_import_status"] = {'''
if needle in text:
    text = text.replace(needle, replacement, 2)
elif 'st.session_state["seller_inventory_triage_result"] = build_seller_inventory_triage(' not in text:
    raise SystemExit("automatic triage import anchors missing")

status_anchor = '''    seller_top5_result = st.session_state.get("seller_top5_result")\n'''
triage_ui = '''    if st.button("🎯 Uppdatera Bästa 20 att undersöka", key="seller_inventory_triage_refresh", use_container_width=True):\n        triage_alias = str(seller_top5_alias or "").strip()\n        if not triage_alias:\n            st.warning("Ange ett säljarnamn först.")\n        else:\n            triage_sport = "hockey" if seller_top5_sport_label == "Hockey" else "football"\n            with st.spinner(f"Prioriterar inlästa annonser från {triage_alias}…"):\n                st.session_state["seller_inventory_triage_result"] = build_seller_inventory_triage(\n                    triage_alias,\n                    get_data(get_data_version()),\n                    analyze_fn=analyze_item,\n                    sport=triage_sport,\n                    max_fast_analyses=120,\n                    top_n=20,\n                )\n\n    triage_result = st.session_state.get("seller_inventory_triage_result")\n    if triage_result and triage_result.get("seller") == str(seller_top5_alias or "").strip():\n        triage_rows = triage_result.get("rows") or []\n        with st.expander("🎯 Bästa 20 att undersöka", expanded=bool(triage_rows)):\n            st.caption(\n                f"{int(triage_result.get('cheap_scanned_count') or 0)} säljarannonser skannade · "\n                f"{int(triage_result.get('fast_analysed_count') or 0)} snabbanalyserade. "\n                "Detta är prioritering för vidare analys, inte KÖP-signaler."\n            )\n            if not triage_rows:\n                st.info("Inga prioriterade kandidater finns i det hittills inlästa säljar-lagret.")\n            for triage_idx, triage_row in enumerate(triage_rows[:20], start=1):\n                triage_title = triage_row.get("title") or "Kortannons"\n                triage_price = triage_row.get("price")\n                triage_score = float(triage_row.get("quick_score") or 0)\n                triage_label = triage_row.get("label") or "UNDERSÖK"\n                st.markdown(f"**#{triage_idx} {triage_title}**")\n                triage_facts = [triage_label, f"prioritet {triage_score:.0f}/100"]\n                if triage_price is not None:\n                    try:\n                        triage_facts.insert(0, f"pris {float(triage_price):.0f} kr")\n                    except (TypeError, ValueError):\n                        pass\n                st.caption(" · ".join(triage_facts))\n                if triage_row.get("reason"):\n                    st.caption(triage_row.get("reason"))\n                if triage_row.get("url"):\n                    st.link_button("Öppna annonsen ↗", triage_row.get("url"), use_container_width=True, key=f"triage_link_{triage_idx}_{str(triage_row.get('url'))[-16:]}")\n                st.divider()\n\n    seller_top5_result = st.session_state.get("seller_top5_result")\n'''
if "🎯 Bästa 20 att undersöka" not in text:
    if status_anchor not in text:
        raise SystemExit("triage UI anchor missing")
    text = text.replace(status_anchor, triage_ui, 1)

path.write_text(text, encoding="utf-8")
print("Seller inventory triage UI patch applied")
