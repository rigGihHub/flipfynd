from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')
original = text

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
elif 'Synkar analysmotorn automatiskt' in text:
    print('already patched')
    raise SystemExit(0)
else:
    raise SystemExit('Seller Top 5 mixed-deploy block not found')

p.write_text(text, encoding='utf-8')
print('patched Seller Top 5 to auto-reload stale controller')
