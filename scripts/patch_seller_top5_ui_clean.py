from pathlib import Path
import re

p = Path('app.py')
text = p.read_text(encoding='utf-8')
original = text

# One-click Seller Top 5 UX: sport choice and the separate import/triage controls
# are obsolete. The controller now fetches the complete seller inventory,
# analyses supported sports together and exposes real progress itself.
text = text.replace(
    '    st.caption("Skriv ett Tradera-säljarnamn. FlipFynd hämtar säljarens aktiva annonser och rankar de fem bästa möjligheterna med samma försiktiga analysregler som i huvudsökningen.")',
    '    st.caption("Ange säljaren och tryck en gång. FlipFynd läser in säljarens annonser, filtrerar till samlarkort, analyserar hockey och fotboll tillsammans och rankar de fem bästa möjligheterna.")',
    1,
)

radio_block = '''    seller_top5_sport_label = st.radio(
        "Sport",
        ["Hockey", "Fotboll"],
        horizontal=True,
        key="seller_top5_sport",
    )
'''
if radio_block in text:
    text = text.replace(radio_block, '    seller_top5_sport_label = "Alla"\n', 1)

text = text.replace(
    'if st.button("🔎 Hitta säljarens 5 bästa fynd", key="seller_top5_run", use_container_width=True):',
    'if st.button("🔎 Läs in & ranka säljarens 5 bästa", key="seller_top5_run", use_container_width=True):',
    1,
)
text = text.replace(
    '            sport_key = "hockey" if seller_top5_sport_label == "Hockey" else "football"',
    '            sport_key = "all"',
    1,
)

# Visible determinate progress in app.py. Do not rely only on st.status/spinners.
progress_anchor = '''            seller_status = st.status(f"🔎 Söker igenom {alias}…", expanded=True)
            seller_progress_line = seller_status.empty()
            seller_status.write("Startar säljarinventering och prioritering av kandidater.")
'''
progress_replacement = '''            seller_status = st.status(f"🔎 Söker igenom {alias}…", expanded=True)
            seller_progress_line = seller_status.empty()
            seller_progress_bar = st.progress(0, text="0% · Startar analysen…")
            seller_status.write("Startar säljarinventering och prioritering av kandidater.")
'''
if progress_anchor in text:
    text = text.replace(progress_anchor, progress_replacement, 1)

callback_anchor = '''                pages_read = int((info or {}).get("pages_read") or 0)
                max_pages = int((info or {}).get("max_pages") or 0)
'''
callback_replacement = '''                pages_read = int((info or {}).get("pages_read") or 0)
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
                    progress_text = f"{progress_percent}% · Hämtar annonser · {found} hittade"
                elif phase.startswith("filter"):
                    progress_text = f"{progress_percent}% · Filtrerar samlarkort" + (f" · {done}/{total}" if total else "")
                elif phase.startswith("quick"):
                    progress_text = f"{progress_percent}% · Snabbanalyserar" + (f" · {done}/{total}" if total else "")
                elif phase.startswith("full"):
                    progress_text = f"{progress_percent}% · Fullanalyserar" + (f" · {done}/{total}" if total else "")
                elif phase == "ranking":
                    progress_text = f"{progress_percent}% · Rankar Top 5"
                elif phase == "complete":
                    progress_text = "100% · Klart"
                else:
                    progress_text = f"{progress_percent}% · Bearbetar…"
                seller_progress_bar.progress(progress_percent, text=progress_text)
'''
if callback_anchor in text and 'progress_percent = (info or {}).get("percent")' not in text:
    text = text.replace(callback_anchor, callback_replacement, 1)

# A stale mixed Streamlit deploy must never enter a long opaque compatibility
# run. Fail fast and ask for one rerun instead; otherwise users see a spinner
# with no measurable progress and may wait indefinitely.
compat_old = '''                    seller_status.write("Deployen synkas fortfarande – använder kompatibilitetsläge.")
                    top5 = resolve_seller_top5(
'''
compat_new = '''                    seller_progress_bar.progress(0, text="Ny version synkas · försök igen om några sekunder")
                    seller_status.update(label="⚠️ Ny version synkas – kör sökningen igen", state="error", expanded=True)
                    st.warning("FlipFynd laddade blandade kodversioner och avbröt i stället för att fastna utan progress. Vänta några sekunder och tryck på knappen igen.")
                    st.stop()
                    top5 = resolve_seller_top5(
'''
if compat_old in text:
    text = text.replace(compat_old, compat_new, 1)

complete_anchor = '''                seller_status.update(label=f"✅ Sökning klar för {alias}", state="complete", expanded=False)
'''
complete_replacement = '''                seller_progress_bar.progress(100, text="100% · Klart")
                seller_status.update(label=f"✅ Sökning klar för {alias}", state="complete", expanded=False)
'''
if complete_anchor in text and 'seller_progress_bar.progress(100, text="100% · Klart")' not in text:
    text = text.replace(complete_anchor, complete_replacement, 1)

error_anchor = '''            except Exception:
                seller_status.update(label=f"❌ Sökningen av {alias} avbröts", state="error", expanded=True)
                raise
'''
error_replacement = '''            except Exception:
                try:
                    seller_progress_bar.progress(0, text="Sökningen avbröts")
                except Exception:
                    pass
                seller_status.update(label=f"❌ Sökningen av {alias} avbröts", state="error", expanded=True)
                raise
'''
if error_anchor in text:
    text = text.replace(error_anchor, error_replacement, 1)

# Remove the now-redundant second import button, cursor handling and separate
# "Bästa 20" triage UI. Keep the Top 5 result rendering immediately after it.
redundant_controls = re.compile(
    r'\n    import_alias = str\(seller_top5_alias or ""\)\.strip\(\).*?'
    r'(?=\n    seller_top5_result = st\.session_state\.get\("seller_top5_result"\))',
    re.S,
)
text, _removed = redundant_controls.subn('\n', text, count=1)

old_legacy = '''        rows = seller_top5_result.get("rows") or []
        if not rows:
            st.info("Inga tillräckligt analyserbara kandidater hittades hos säljaren just nu.")
        for idx, row in enumerate(rows[:5], start=1):
            title = row.get("title") or "Kortannons"
            price = row.get("price")
            decision = str(row.get("decision") or "UNDERSÖK")
            label = row.get("label") or "BEHÖVER VERIFIERAS"
            st.markdown(f"**#{idx} {title}**")
            facts = []
            if price is not None:
                try:
                    facts.append(f"pris {float(price):.0f} kr")
                except (TypeError, ValueError):
                    pass
            facts.append(decision)
            facts.append(label)
            st.caption(" · ".join(facts))
            sold = int(row.get("sold_comps") or 0)
            edge = float(row.get("market_edge") or 0)
            st.caption(f"Exact SOLD: {sold} · market edge: {edge:.0f}/100")
            if row.get("reason"):
                st.caption(row.get("reason"))
            if row.get("url"):
                st.link_button("Öppna annonsen ↗", row.get("url"), use_container_width=True)
            st.divider()
'''

old_current = '''        rows = seller_top5_result.get("rows") or []
        rejected_count = int(seller_top5_result.get("domain_rejected_count") or 0)
        card_count = int(seller_top5_result.get("card_inventory_count") or 0)
        if rejected_count:
            st.caption(f"{rejected_count} tydliga icke-kortannonser filtrerades bort före analys. {card_count} annonser återstod som kortkandidater.")
        if not rows:
            st.info("Inga starka fynd hittades i det analyserade säljar-lagret just nu.")
        for idx, row in enumerate(rows[:5], start=1):
            title = row.get("title") or "Kortannons"
            price = row.get("price")
            decision = str(row.get("decision") or "UNDERSÖK").upper()
            badge = "🟢 KÖP" if decision.startswith("KÖP") else "🟡 Värt att undersöka"
            st.markdown(f"#### #{idx} {title}")
            if price is not None:
                try:
                    st.markdown(f"**{float(price):.0f} kr** · {badge}")
                except (TypeError, ValueError):
                    st.markdown(badge)
            else:
                st.markdown(badge)
            reason = str(row.get("reason") or "").strip()
            if reason:
                st.caption(reason)
            elif decision.startswith("UNDERSÖK"):
                st.caption("Lovande kandidat, men FlipFynd behöver mer verifierad identitet eller marknadsdata innan köp kan rekommenderas.")
            with st.expander("Visa analysdetaljer", expanded=False):
                sold = int(row.get("sold_comps") or 0)
                edge = float(row.get("market_edge") or 0)
                valuation = float(row.get("valuation_confidence") or 0)
                st.caption(f"Exact SOLD: {sold} · market edge: {edge:.0f}/100 · värderingssäkerhet: {valuation:.0f}/100")
                if row.get("label"):
                    st.caption(str(row.get("label")))
            if row.get("url"):
                st.link_button("Öppna annonsen ↗", row.get("url"), use_container_width=True)
            st.divider()
'''

new = '''        rows = seller_top5_result.get("rows") or []
        rejected_count = int(seller_top5_result.get("domain_rejected_count") or 0)
        card_count = int(seller_top5_result.get("card_inventory_count") or 0)
        if rejected_count:
            st.caption(f"{rejected_count} tydliga icke-kortannonser filtrerades bort. {card_count} kortkandidater återstod.")
        if seller_top5_result.get("ranking_source") == "ORDINARY_FLIPFYND_RANK":
            st.caption("Top 5 rankas med samma fullanalys och slutranking som den ordinarie FlipFynd-sökningen.")
        sport_counts = seller_top5_result.get("sport_counts") or {}
        if sport_counts:
            st.caption(f"Analyserat tillsammans: {int(sport_counts.get('hockey') or 0)} hockey · {int(sport_counts.get('football') or 0)} fotboll.")
        if not rows:
            st.info("Inga samlarkort kunde rankas hos säljaren just nu.")
        for idx, row in enumerate(rows[:5], start=1):
            title = row.get("title") or "Kortannons"
            price = row.get("price")
            decision = str(row.get("decision") or "SKIP").upper()
            if decision.startswith("KÖP"):
                badge = "🟢 KÖP"
            elif decision.startswith("UNDERSÖK"):
                badge = "🟡 Värt att undersöka"
            else:
                badge = "⚪ Bäst av resten"
            st.markdown(f"#### #{idx} {title}")
            if price is not None:
                try:
                    st.markdown(f"**{float(price):.0f} kr** · {badge}")
                except (TypeError, ValueError):
                    st.markdown(badge)
            else:
                st.markdown(badge)
            reason = str(row.get("reason") or "").strip()
            if reason:
                st.caption(reason)
            with st.expander("Visa analysdetaljer", expanded=False):
                if row.get("sport"):
                    st.write(f"**Sport:** {'Hockey' if row.get('sport') == 'hockey' else 'Fotboll'}")
                st.write(f"**Ordinarie rank:** {float(row.get('rank_score') or 0):.0f}")
                st.write(f"**Spelarscore:** {float(row.get('player_market_score') or 0):.0f}/100")
                st.write(f"**Riskjusterad vinst:** {float(row.get('risk_adjusted_profit') or 0):.0f} kr")
                st.write(f"**Exact SOLD:** {int(row.get('sold_comps') or 0)}")
                st.write(f"**Market edge:** {float(row.get('market_edge') or 0):.0f}/100")
                st.write(f"**Värderingssäkerhet:** {float(row.get('valuation_confidence') or 0):.0f}/100")
                if row.get("analysis_level") == "quick_fallback":
                    st.warning("Detta reservresultat är endast snabbanalyserat.")
            if row.get("url"):
                st.link_button("Öppna annonsen ↗", row.get("url"), use_container_width=True)
            st.divider()
'''

if old_current in text:
    text = text.replace(old_current, new, 1)
elif old_legacy in text:
    text = text.replace(old_legacy, new, 1)

if text == original:
    print('already patched')
else:
    p.write_text(text, encoding='utf-8')
    print('patched Seller Top 5 one-click UI with determinate progress')
