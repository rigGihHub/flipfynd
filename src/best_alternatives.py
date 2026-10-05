"""Always present the best available five without changing valuation evidence."""
from math import isfinite
from urllib.parse import urlsplit

from src.opportunity_top5 import build_opportunity_top5, listing_url, has_supported_price_context
from src.seller_profit_display import build_seller_net_profit_summary
from src.collector_evidence import acquisition_breakdown, money as evidence_money, render_listing_review
from src.card_parser import clean_card_title
from src.search_product_policy import product_scope


def _number(value):
    try:
        value = float(value)
        return value if isfinite(value) else None
    except (TypeError, ValueError):
        return None


def build_best_alternatives(results, *, research_leads=(), extra_rows=()):
    pool, positions, excluded = [], {}, set()
    def add(raw):
        if not isinstance(raw, dict):
            return
        item = dict(raw)
        url = listing_url(item)
        title = item.get('titel') or item.get('title')
        if not title:
            return
        if not product_scope(item)["allowed"]:
            excluded.add(url or str(title).casefold())
            return
        parts = urlsplit(url or '')
        marker = (parts.netloc, parts.path.rstrip('/')) if url else str(title).casefold()
        scenario = item.get('asking_price_opportunity') or {}
        if _number(scenario.get('total_cost')) is not None:
            item['analysis_total_cost'] = scenario['total_cost']
        if marker in positions:
            existing = pool[positions[marker]]
            if scenario and not existing.get('asking_price_opportunity'):
                existing['asking_price_opportunity'] = scenario
                if item.get('analysis_total_cost') is not None:
                    existing['analysis_total_cost'] = item['analysis_total_cost']
            return
        positions[marker] = len(pool)
        pool.append(item)
    for row in results or []:
        add(row)
    for row in extra_rows or []:
        add(row)
    for lead in research_leads or []:
        if isinstance(lead, dict):
            add({'titel': lead.get('title'), 'lank': lead.get('url'),
                 'asking_price_opportunity': lead.get('scenario') or {}})
    result = build_opportunity_top5(pool, limit=len(pool), fill_alternatives=True)
    ranked = result['rows']
    result['rows'] = ranked[:5]
    result['review_candidates'] = [row for row in ranked[5:]
        if not has_supported_price_context(row)
        or (row.get('decision') != 'AVSTÅ' and (_number(row.get('practical_margin')) or 0) > 0)][:15]
    result['available_count'] = len(pool)
    result['product_scope_excluded_count'] = len(excluded)
    return result


def alternative_status(row):
    if row.get('decision') == 'KÖP':
        return 'KÖP · verifierat underlag'
    margin = _number(row.get('practical_margin'))
    source = row.get('practical_price_source')
    if source == 'MODEL_GUIDE':
        return 'Potentiell kandidat · endast modell/guide'
    if source == 'ACTIVE_PRICE' and int(row.get('asking_comparison_count') or 0) < 2:
        return ('Osäkert · endast ett jämförelsepris' if int(row.get('asking_comparison_count') or 0) == 1
                else 'Potentiell kandidat · prisunderlag behöver verifieras')
    if margin is None:
        return 'Potentiell kandidat · prisunderlag saknas'
    if row.get('decision') == 'AVSTÅ' or (margin is not None and margin <= 0):
        return 'AVSTÅ · ingen positiv marginal'
    roi = _number(row.get('practical_roi'))
    if margin < 35 or (roi is not None and roi < .15):
        return 'Svag marginal · inget fynd'
    return 'UNDERSÖK · köp ej bekräftat'


def render_best_alternatives(result, *, explain=None, seller=None):
    import streamlit as st
    rows = result.get('rows') or []
    st.markdown('### 🏆 De 5 bästa alternativen')
    st.caption('Bäst bland de tillgängliga alternativen i din sökning. En plats i listan betyder inte att kortet är ett lönsamt köp.')
    if any(str((row.get('_source_item') or {}).get('source_category') or '').casefold().find('fotboll') >= 0 for row in rows):
        st.caption('Utan ett styrkt fynd prioriteras numrerade kort, autografer, relikkort och identifierade hobbyserier framför vanliga inserts med svaga modellvärden.')
    if result.get('product_scope_excluded_count'):
        st.caption(f"{result['product_scope_excluded_count']} annonser uteslutna av produktfiltret. Match Attax, Adrenalyn och vanliga Beast Mode-inserts fyller inte topplistan.")
    if len(rows) < 5:
        st.info(f'Endast {len(rows)} unika alternativ finns i det analyserade underlaget. Listan fylls på när fler har analyserats.')
    if not rows:
        return
    table = []
    def money(value):
        number = _number(value)
        return f'{number:.0f} kr' if number is not None else 'Saknas'
    for rank, row in enumerate(rows, 1):
        summary = build_seller_net_profit_summary(row)
        indication = row.get('market_value') or row.get('asking_reference') or row.get('heuristic_indication')
        source = 'SOLD/verifierat' if row.get('market_value') is not None else (
            'Begärda priser' if row.get('asking_reference') is not None else (
                'Modell/guide' if row.get('heuristic_indication') is not None else 'Saknas'))
        net = (('Scenario ' if summary['evidence_kind'] == 'ACTIVE_ASKING' else '')
               + f"{summary['value']:+.0f} kr") if summary['available'] else 'Ej beräkningsbar'
        table.append({'#': rank, 'Kort': clean_card_title(row['title']), 'Bedömning': alternative_status(row),
                      'Total kostnad': money(row.get('total_cost')), 'Prisindikation': money(indication),
                      'Underlag': source, 'Netto / scenario': net,
                      'Fyndpotential': f"{float(row.get('potential') or 0):.0f}/100",
                      'Säkerhet': f"{float(row.get('certainty') or 0):.0f}/100"})
    st.dataframe(table, use_container_width=True, hide_index=True)
    for rank, row in enumerate(rows, 1):
        with st.expander(f"#{rank} · {clean_card_title(row['title'])}", expanded=False):
            st.write('**' + alternative_status(row) + '**')
            source_item = row.get('_source_item') or {}
            scenario = source_item.get('asking_price_opportunity') or {}
            price = scenario.get('purchase_price', source_item.get('pris', source_item.get('price')))
            shipping = scenario.get('shipping', source_item.get('frakt', source_item.get('shipping')))
            costs = acquisition_breakdown(source_item, row.get('total_cost'))
            st.caption(' · '.join(label + ' ' + evidence_money(value) for label, value in costs['parts'])
                       + ' · total kostnad ' + evidence_money(costs['total']))
            summary = build_seller_net_profit_summary(row)
            if summary['available']:
                st.write(f"{summary['label']}: **{summary['value']:+.2f} kr**")
                st.caption(summary['basis'])
            else:
                st.caption('Nettovinst kan inte beräknas med tillräckligt underlag.')
            render_listing_review(source_item, total_cost=row.get('total_cost'))
            if row.get('reasons'):
                st.caption('Varför: ' + ' · '.join(row['reasons']))
            if row.get('primary_blocker'):
                st.caption('Kontrollera först: ' + row['primary_blocker'])
            if explain:
                explain(source_item, f'top5_{rank}')
            if seller:
                seller(source_item, f'top5_{rank}')
            if row.get('url'):
                st.link_button('Öppna annonsen ↗', row['url'], use_container_width=True)
    review = result.get('review_candidates') or []
    if review:
        with st.expander(f'Fler potentiella kandidater ({len(review)})', expanded=False):
            st.caption('Ytterligare kort att granska. Saknade jämförpriser eller ett lågt modellvärde räcker inte för att avfärda dem. Dessa är inga bekräftade köp.')
            for rank, row in enumerate(review, 6):
                st.markdown(f"**{rank}. {clean_card_title(row['title'])}**")
                st.caption(alternative_status(row) + ' · total kostnad ' + money(row.get('total_cost')))
                if row.get('primary_blocker'):
                    st.caption('Kontrollera först: ' + row['primary_blocker'])
                if row.get('url'):
                    st.link_button('Öppna annonsen ↗', row['url'], key=f'review_candidate_{rank}', use_container_width=True)
