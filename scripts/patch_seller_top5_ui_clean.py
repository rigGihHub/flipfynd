from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')
original = text

# Keep mixed Streamlit deploys self-healing.
old = '''                except TypeError as exc:
                    # Streamlit Cloud can briefly serve a mixed deploy where app.py is newer
                    # than seller_top5_controller.py. Retry the legacy signature instead of
                    # taking down the whole app. Only swallow the known signature mismatch.
                    if "profile_url" not in str(exc) and "progress_callback" not in str(exc):
                        raise
                    seller_progress_bar.progress(0, text="Ny version synkas · försök igen om några sekunder")
                    seller_status.update(label="⚠️ Ny version synkas – kör sökningen igen", state="error", expanded=True)
                    st.warning("FlipFynd laddade blandade kodversioner och avbröt i stället för att fastna utan progress. Vänta några sekunder och tryck på knappen igen.")
                    st.stop()
                    top5 = resolve_seller_top5(
                        alias,
                        local_market,
                        analyze_fn=analyze_item,
                        sport=sport_key,
                        credentials=creds,
                        quick_limit=60,
                        full_limit=10,
                    )
'''
new = '''                except TypeError as exc:
                    # Streamlit may hot-reload app.py while keeping an older imported
                    # controller module in memory. Refresh that module automatically and
                    # continue the same user action instead of asking for another click.
                    if "profile_url" not in str(exc) and "progress_callback" not in str(exc):
                        raise
                    seller_progress_bar.progress(2, text="2% · Synkar analysmotorn automatiskt…")
                    seller_progress_line.info("Ny kod upptäcktes · laddar om Seller Top 5-motorn utan att avbryta sökningen")
                    import importlib
                    import src.seller_top5_controller as _seller_top5_controller
                    _seller_top5_controller = importlib.reload(_seller_top5_controller)
                    top5 = _seller_top5_controller.resolve_seller_top5(
                        alias,
                        local_market,
                        analyze_fn=analyze_item,
                        sport="all",
                        credentials=creds,
                        profile_url=seller_top5_profile_url_resolved,
                        progress_callback=_seller_search_progress,
                        quick_limit=60,
                        full_limit=10,
                    )
'''
if old in text:
    text = text.replace(old, new, 1)

# One button becomes an explicit continuation button while a public inventory
# checkpoint is incomplete.
button_old = '''    if st.button("🔎 Läs in & ranka säljarens 5 bästa", key="seller_top5_run", use_container_width=True):
'''
button_new = '''    _seller_previous_result = st.session_state.get("seller_top5_result") or {}
    _seller_continue_inventory = str(_seller_previous_result.get("status") or "") == "INVENTORY_PARTIAL"
    _seller_button_label = "📥 Fortsätt läsa nästa 10 sidor" if _seller_continue_inventory else "🔎 Läs in & ranka säljarens 5 bästa"
    if st.button(_seller_button_label, key="seller_top5_run", use_container_width=True):
'''
if button_old in text:
    text = text.replace(button_old, button_new, 1)

# Never present a local fallback as the seller's complete Top 5 when the user
# explicitly supplied a public Tradera profile URL.
save_old = '''                st.session_state["seller_top5_result"] = top5
                found_count = int(top5.get("inventory_count") or 0)
'''
save_new = '''                if seller_top5_profile_url_resolved and top5.get("inventory_source") == "LOCAL_MARKET":
                    top5 = dict(top5)
                    top5["status"] = "PROFILE_INCOMPLETE"
                    top5["rows"] = []
                st.session_state["seller_top5_result"] = top5
                found_count = int(top5.get("inventory_count") or 0)
'''
if save_old in text:
    text = text.replace(save_old, save_new, 1)

# Partial inventory blocks are successful checkpoints, not completed rankings.
complete_old = '''                seller_status.write(
                    f"{found_count} annonser hittade · {quick_count} snabbanalyserade · "
                    f"{full_count} fullanalyserade · källa: {source}."
                )
                seller_progress_bar.progress(100, text="100% · Klart")
                seller_status.update(label=f"✅ Sökning klar för {alias}", state="complete", expanded=False)
'''
complete_new = '''                result_status = str(top5.get("status") or "")
                if result_status == "INVENTORY_PARTIAL":
                    pages_read = int(top5.get("public_pages_read") or 0)
                    next_page = int(top5.get("public_next_page") or 1)
                    seller_progress_bar.progress(20, text=f"20% · {found_count} annonser sparade")
                    seller_status.write(f"{pages_read} profilsidor lästa totalt · {found_count} annonser sparade · nästa block börjar på sida {next_page}.")
                    seller_status.update(label=f"📥 10-sidorsblock klart för {alias}", state="complete", expanded=False)
                elif result_status == "PROFILE_INCOMPLETE":
                    seller_progress_bar.progress(0, text="Profilinläsningen behöver fortsätta")
                    seller_status.update(label=f"⚠️ Hela profilen för {alias} är inte inläst", state="error", expanded=True)
                else:
                    seller_status.write(
                        f"{found_count} annonser hittade · {quick_count} snabbanalyserade · "
                        f"{full_count} fullanalyserade · källa: {source}."
                    )
                    seller_progress_bar.progress(100, text="100% · Klart")
                    seller_status.update(label=f"✅ Sökning klar för {alias}", state="complete", expanded=False)
'''
if complete_old in text:
    text = text.replace(complete_old, complete_new, 1)

# Render checkpoint state separately and suppress a fake Top 5 until inventory
# collection is complete.
result_old = '''    seller_top5_result = st.session_state.get("seller_top5_result")
    if seller_top5_result:
'''
result_new = '''    seller_top5_result = st.session_state.get("seller_top5_result")
    _seller_result_status = str((seller_top5_result or {}).get("status") or "")
    if seller_top5_result and _seller_result_status == "INVENTORY_PARTIAL":
        _saved = int(seller_top5_result.get("inventory_count") or 0)
        _pages = int(seller_top5_result.get("public_pages_read") or 0)
        _next = int(seller_top5_result.get("public_next_page") or 1)
        st.info(f"📥 Inventering pågår: {_pages} profilsidor lästa och {_saved} unika annonser sparade. Nästa block börjar på sida {_next}. Tryck på ‘Fortsätt läsa nästa 10 sidor’. Top 5 rankas först när hela profilen är inläst.")
    elif seller_top5_result and _seller_result_status == "PROFILE_INCOMPLETE":
        st.warning("Hela Tradera-profilen kunde inte verifieras som inläst. FlipFynd visar därför ingen Top 5 från den lokala fallback-datan. Kör profilinläsningen igen/fortsätt nästa block.")
    if seller_top5_result and _seller_result_status not in {"INVENTORY_PARTIAL", "PROFILE_INCOMPLETE"}:
'''
if result_old in text:
    text = text.replace(result_old, result_new, 1)

# Explicit completion message once the public seller profile has been exhausted.
source_old = '''        elif inventory_source == "TRADERA_PUBLIC_PROFILE":
            pages_read = int(seller_top5_result.get("public_pages_read") or 0)
            st.caption(f"Källa: säljarens publika Tradera-profil · {pages_read} profilsidor lästa.")
'''
source_new = '''        elif inventory_source == "TRADERA_PUBLIC_PROFILE":
            pages_read = int(seller_top5_result.get("public_pages_read") or 0)
            st.caption(f"Källa: säljarens publika Tradera-profil · {pages_read} profilsidor lästa.")
            if seller_top5_result.get("public_inventory_complete"):
                st.success("✅ Alla säljarens annonser är inlästa. Top 5 är rankad på hela det hittade lagret.")
'''
if source_old in text:
    text = text.replace(source_old, source_new, 1)

if text == original:
    print('already patched')
else:
    p.write_text(text, encoding='utf-8')
    print('patched Seller Top 5 checkpoint UI and completion state')
