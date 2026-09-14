from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

old = '''            with st.spinner(f"Hämtar och analyserar annonser från {alias}…"):
                top5 = resolve_seller_top5(
                    alias,
                    local_market,
                    analyze_fn=analyze_item,
                    sport=sport_key,
                    credentials=creds,
                    profile_url=seller_top5_profile_url,
                    quick_limit=60,
                    full_limit=10,
                )
                st.session_state["seller_top5_result"] = top5
'''

new = '''            seller_status = st.status(f"🔎 Söker igenom {alias}…", expanded=True)
            seller_status.write("Startar säljarinventering och prioritering av kandidater.")
            try:
                try:
                    top5 = resolve_seller_top5(
                        alias,
                        local_market,
                        analyze_fn=analyze_item,
                        sport=sport_key,
                        credentials=creds,
                        profile_url=seller_top5_profile_url,
                        quick_limit=60,
                        full_limit=10,
                    )
                except TypeError as exc:
                    # Streamlit Cloud can briefly serve a mixed deploy where app.py is newer
                    # than seller_top5_controller.py. Retry the legacy signature instead of
                    # taking down the whole app. Only swallow the known signature mismatch.
                    if "profile_url" not in str(exc):
                        raise
                    seller_status.write("Deployen synkas fortfarande – använder kompatibilitetsläge.")
                    top5 = resolve_seller_top5(
                        alias,
                        local_market,
                        analyze_fn=analyze_item,
                        sport=sport_key,
                        credentials=creds,
                        quick_limit=60,
                        full_limit=10,
                    )
                st.session_state["seller_top5_result"] = top5
                found_count = int(top5.get("inventory_count") or 0)
                quick_count = int(top5.get("quick_analysed") or 0)
                full_count = int(top5.get("full_analysed") or 0)
                source = top5.get("inventory_source") or "okänd källa"
                seller_status.write(
                    f"{found_count} annonser hittade · {quick_count} snabbanalyserade · "
                    f"{full_count} fullanalyserade · källa: {source}."
                )
                seller_status.update(label=f"✅ Sökning klar för {alias}", state="complete", expanded=False)
            except Exception:
                seller_status.update(label=f"❌ Sökningen av {alias} avbröts", state="error", expanded=True)
                raise
'''

if old not in text:
    if 'seller_status = st.status(f"🔎 Söker igenom {alias}…"' in text:
        print('Patch already applied')
    else:
        raise SystemExit('Seller Top 5 call block not found')
else:
    text = text.replace(old, new, 1)
    path.write_text(text, encoding='utf-8')
    print('Seller search compatibility/progress patch applied')
