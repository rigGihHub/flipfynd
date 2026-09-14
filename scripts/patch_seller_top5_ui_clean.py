from pathlib import Path

p = Path('app.py')
text = p.read_text(encoding='utf-8')

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
elif 'Top 5 rankas med samma fullanalys och slutranking' in text:
    print('already patched')
    raise SystemExit(0)
else:
    raise SystemExit('seller top5 render block not found')

p.write_text(text, encoding='utf-8')
print('patched seller top5 UI to ordinary ranking contract')
