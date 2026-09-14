from pathlib import Path
import re

p = Path('app.py')
text = p.read_text(encoding='utf-8')
original = text

# Version bump for the UX pass.
text = text.replace('APP_VERSION = "v0.12.83"', 'APP_VERSION = "v0.12.84"', 1)

# Give the mobile sidebar enough room so status copy does not wrap word-by-word.
mobile_css_old = '''@media (max-width: 640px) {
  .stApp { background-size: 24px 24px, 24px 24px, auto; }
  [data-testid="stMetric"], [data-testid="stExpander"], div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 10px;
  }
}'''
mobile_css_new = '''@media (max-width: 640px) {
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
}'''
if mobile_css_old in text:
    text = text.replace(mobile_css_old, mobile_css_new, 1)

# Remove duplicated hot-patch artefacts so the user sees one coherent flow.
query_block = '''    try:
        if seller_top5_alias and str(st.query_params.get("seller", "") or "") != str(seller_top5_alias):
            st.query_params["seller"] = str(seller_top5_alias)
        if seller_top5_profile_url and str(st.query_params.get("seller_profile", "") or "") != str(seller_top5_profile_url):
            st.query_params["seller_profile"] = str(seller_top5_profile_url)
    except Exception:
        pass
'''
while text.count(query_block) > 1:
    first = text.find(query_block)
    second = text.find(query_block, first + len(query_block))
    text = text[:second] + text[second + len(query_block):]

guard_block = '''                if seller_top5_profile_url_resolved and top5.get("inventory_source") == "LOCAL_MARKET":
                    top5 = dict(top5)
                    top5["status"] = "PROFILE_INCOMPLETE"
                    top5["rows"] = []
'''
while text.count(guard_block) > 1:
    first = text.find(guard_block)
    second = text.find(guard_block, first + len(guard_block))
    text = text[:second] + text[second + len(guard_block):]

success_block = '''            if seller_top5_result.get("public_inventory_complete"):
                st.success("✅ Alla säljarens annonser är inlästa. Top 5 är rankad på hela det hittade lagret.")
'''
while text.count(success_block) > 1:
    first = text.find(success_block)
    second = text.find(success_block, first + len(success_block))
    text = text[:second] + text[second + len(success_block):]

# Shorter, action-oriented copy.
text = text.replace(
    '    st.caption("Ange säljaren och tryck en gång. FlipFynd läser in säljarens annonser, filtrerar till samlarkort, analyserar hockey och fotboll tillsammans och rankar de fem bästa möjligheterna.")',
    '    st.caption("Läs in en Tradera-säljare och se de bästa korten medan sökningen fortsätter.")',
    1,
)
text = text.replace('"Säljarnamn"', '"Säljare"', 1)
text = text.replace('"Tradera-profillänk (valfri)"', '"Tradera-profil"', 1)
text = text.replace(
    'help="Behövs som fallback när Tradera API saknas. Öppna säljarens profilsida på Tradera och klistra in länken."',
    'help="Klistra in säljarens profilsida, till exempel https://www.tradera.com/profile/items/5412219/"',
    1,
)
text = text.replace(
    '_seller_button_label = "📥 Fortsätt läsa nästa 5 sidor" if _seller_continue_inventory else "🔎 Läs in & ranka säljarens 5 bästa"',
    '_seller_button_label = "Fortsätt söka" if _seller_continue_inventory else "🔎 Hitta säljarens bästa kort"',
    1,
)

# Keep one progress indicator visible and push technical detail into the collapsed status box.
text = text.replace(
    'seller_status = st.status(f"🔎 Söker igenom {alias}…", expanded=True)',
    'seller_status = st.status(f"🔎 Söker {alias}", expanded=False)',
    1,
)
text = text.replace('seller_progress_bar = st.progress(0, text="0% · Startar analysen…")', 'seller_progress_bar = st.progress(0, text="Startar…")', 1)
text = text.replace('            seller_status.write("Startar säljarinventering och prioritering av kandidater.")\n', '', 1)

# Concise progress labels for narrow mobile screens.
text = text.replace('progress_text = f"{progress_percent}% · Hämtar annonser · {found} hittade"', 'progress_text = f"{progress_percent}% · {found} annonser hittade"', 1)
text = text.replace('progress_text = f"{progress_percent}% · Filtrerar samlarkort" + (f" · {done}/{total}" if total else "")', 'progress_text = f"{progress_percent}% · Filtrerar kort" + (f" · {done}/{total}" if total else "")', 1)
text = text.replace('progress_text = f"{progress_percent}% · Snabbanalyserar" + (f" · {done}/{total}" if total else "")', 'progress_text = f"{progress_percent}% · Prioriterar" + (f" · {done}/{total}" if total else "")', 1)
text = text.replace('progress_text = f"{progress_percent}% · Fullanalyserar" + (f" · {done}/{total}" if total else "")', 'progress_text = f"{progress_percent}% · Analyserar toppkandidater" + (f" · {done}/{total}" if total else "")', 1)
text = text.replace('seller_progress_line.info(f"📄 Läser profilsida {page} · {found} unika annonser hittade hittills")', 'seller_progress_line.caption(f"Sida {page} · {found} annonser")', 1)
text = text.replace('seller_progress_line.success(f"Sida {page} klar · {found} unika annonser hittade · {pages_read}/{max_pages} sidor i detta block")', 'seller_progress_line.caption(f"Sida {page} klar · {found} annonser")', 1)
text = text.replace('seller_progress_line.success(f"Profilens slut nått vid sida {page} · {found} unika annonser hittade")', 'seller_progress_line.caption(f"Alla sidor lästa · {found} annonser")', 1)
text = text.replace('seller_progress_line.info(f"Inventering klar · {found} annonser · går vidare till analys")', 'seller_progress_line.caption(f"{found} annonser · rankar bästa korten")', 1)

# Partial states should be compact and obvious, not large blue/yellow diagnostic cards.
partial_old = '''        if seller_top5_result.get("resume_required"):
            st.warning(f"📥 Inläsningen avbröts, men checkpointen är sparad. {_pages} profilsidor och {_saved} annonser är bevarade. Tryck på ‘Fortsätt läsa nästa 5 sidor’ för att fortsätta från sida {_next}.")
        else:
            st.info(f"📥 Inventering pågår: {_pages} profilsidor lästa och {_saved} unika annonser sparade. Nästa block börjar på sida {_next}. Preliminär Top 5 uppdateras löpande; tryck på ‘Fortsätt läsa nästa 5 sidor’.")
'''
partial_new = '''        if seller_top5_result.get("resume_required"):
            st.caption(f"Sökningen pausades · {_pages} sidor och {_saved} annonser sparade · fortsätter från sida {_next}.")
        else:
            st.caption(f"Sökning pågår · {_pages} sidor · {_saved} annonser · nästa sida {_next}.")
'''
if partial_old in text:
    text = text.replace(partial_old, partial_new, 1)
text = text.replace(
    '        st.warning("Hela Tradera-profilen kunde inte verifieras som inläst. FlipFynd visar därför ingen Top 5 från den lokala fallback-datan. Kör profilinläsningen igen/fortsätt nästa block.")',
    '        st.caption("Profilen är inte färdigläst ännu. Tryck på Fortsätt söka.")',
    1,
)

# Clearer ranking copy and less internal plumbing in the main surface.
text = text.replace('st.markdown(f"### 🏆 Preliminär Top 5 hos {seller_name}")', 'st.markdown(f"### 🏆 Bästa fynd just nu · {seller_name}")', 1)
text = text.replace(
    'st.caption("Listan uppdateras när fler 5-sidorsblock läses in. Kort kan flytta upp, ner eller försvinna när bättre fynd hittas.")',
    'st.caption("Preliminär lista · uppdateras när fler annonser hittas.")',
    1,
)
text = text.replace('st.markdown(f"### 🏆 Slutlig Top 5 hos {seller_name}")', 'st.markdown(f"### 🏆 Slutlig Top 5 · {seller_name}")', 1)

meta_old = '''        st.caption(
            f"{inv_count} annonser hittades · "
            f"{int(seller_top5_result.get('quick_analysed') or 0)} snabbanalyserade · "
            f"{int(seller_top5_result.get('full_analysed') or 0)} fullanalyserade"
        )
'''
meta_new = '''        st.caption(
            f"{inv_count} annonser hittade · "
            f"{int(seller_top5_result.get('full_analysed') or 0)} djupanalyserade"
        )
'''
if meta_old in text:
    text = text.replace(meta_old, meta_new, 1)

# Do not repeat completion banners. A single compact confirmation is enough.
text = text.replace(
    'st.success("✅ Alla säljarens annonser är inlästa. Top 5 är rankad på hela det hittade lagret.")',
    'st.caption("✅ Hela säljarprofilen är inläst.")',
)

# Make weak results explicit without exposing internal SKIP terminology.
text = text.replace('badge = "⚪ Bäst av resten"', 'badge = "⚪ Kandidat · ej verifierad"', 1)

# Show the decision-driving score on the card, while keeping diagnostic metrics collapsed.
price_block = '''            if price is not None:
                try:
                    st.markdown(f"**{float(price):.0f} kr** · {badge}")
                except (TypeError, ValueError):
                    st.markdown(badge)
            else:
                st.markdown(badge)
'''
price_new = '''            _rank_score = float(row.get("rank_score") or 0)
            if price is not None:
                try:
                    st.markdown(f"**{float(price):.0f} kr** · {badge}")
                except (TypeError, ValueError):
                    st.markdown(badge)
            else:
                st.markdown(badge)
            st.caption(f"FlipFynd-score {_rank_score:.0f}/100")
'''
if price_block in text:
    text = text.replace(price_block, price_new, 1)

# Compact the analysis expander into two readable lines instead of a tall metric stack.
detail_old = '''            with st.expander("Visa analysdetaljer", expanded=False):
                st.write(f"**Ordinarie rank:** {float(row.get('rank_score') or 0):.0f}")
                st.write(f"**Spelarscore:** {float(row.get('player_market_score') or 0):.0f}/100")
                st.write(f"**Riskjusterad vinst:** {float(row.get('risk_adjusted_profit') or 0):.0f} kr")
                st.write(f"**Exact SOLD:** {int(row.get('sold_comps') or 0)}")
                st.write(f"**Market edge:** {float(row.get('market_edge') or 0):.0f}/100")
                st.write(f"**Värderingssäkerhet:** {float(row.get('valuation_confidence') or 0):.0f}/100")
                if row.get("analysis_level") == "quick_fallback":
                    st.warning("Detta reservresultat är endast snabbanalyserat.")
'''
detail_new = '''            with st.expander("Analysdetaljer", expanded=False):
                st.caption(
                    f"Spelare {float(row.get('player_market_score') or 0):.0f}/100 · "
                    f"Market edge {float(row.get('market_edge') or 0):.0f}/100 · "
                    f"Värderingssäkerhet {float(row.get('valuation_confidence') or 0):.0f}/100"
                )
                st.caption(
                    f"Exact SOLD {int(row.get('sold_comps') or 0)} · "
                    f"riskjusterad vinst {float(row.get('risk_adjusted_profit') or 0):.0f} kr"
                )
                if row.get("analysis_level") == "quick_fallback":
                    st.caption("Preliminär analys – djupanalys återstår.")
'''
if detail_old in text:
    text = text.replace(detail_old, detail_new, 1)

# Keep source/debug plumbing behind a single collapsed details section by making captions shorter.
text = text.replace('st.caption(f"Källa: säljarens publika Tradera-profil · {pages_read} profilsidor lästa.")', 'st.caption(f"Tradera-profil · {pages_read} sidor lästa")', 1)
text = text.replace('st.caption("Källa: live-inventarie via Tradera API.")', 'st.caption("Live via Tradera")', 1)
text = text.replace('st.caption("Top 5 rankas med samma fullanalys och slutranking som den ordinarie FlipFynd-sökningen.")', 'st.caption("Samma rankingmotor som i ordinarie FlipFynd-sökningen.")', 1)

if text == original:
    print('Seller Top 5 mobile UX already applied')
else:
    p.write_text(text, encoding='utf-8')
    print('Applied Seller Top 5 mobile UX cleanup and version v0.12.84')
