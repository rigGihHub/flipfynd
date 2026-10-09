"""Always present the best available five without changing valuation evidence."""
from math import isfinite
from urllib.parse import urlsplit

from src.opportunity_top5 import build_opportunity_top5, listing_url, has_supported_price_context
from src.seller_profit_display import build_seller_net_profit_summary
from src.collector_evidence import acquisition_breakdown, money as evidence_money, render_listing_review
from src.card_parser import clean_card_title
from src.search_product_policy import product_scope
from src.candidate_review import build_candidate_review


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
    result = build_opportunity_top5(pool, limit=len(pool), fill_alternatives=True, use_model_indications=False)
    ranked = result['rows']
    for row in ranked[:20]:
        row['candidate_review'] = build_candidate_review(row.get('_source_item') or row)
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


def candidate_status(row):
    margin = _number(row.get('practical_margin'))
    if row.get('decision') == 'AVSTÅ' or (margin is not None and margin <= 0):
        return 'Avstå'
    if row.get('decision') == 'KÖP':
        return 'Köpunderlag finns'
    return 'Granska'


def candidate_images(row):
    """Only actual listing URLs; never generated card pictures."""
    images = []
    for item in (row.get('_source_item') or {}, row.get('source_item') or {}, row):
        for key in ('detail_image_urls', 'image_urls', 'visual_image_urls'):
            values = item.get(key) or []
            if isinstance(values, str):
                values = [values]
            for value in values:
                if not isinstance(value, str):
                    continue
                parts = urlsplit(value)
                if parts.scheme in ('https', 'http') and parts.netloc and value not in images:
                    images.append(value)
    return images[:6]


def candidate_presentation(row):
    review = row.get('candidate_review') or build_candidate_review(row.get('_source_item') or row)
    summary = build_seller_net_profit_summary(row)
    indication = row.get('market_value')
    if indication is None:
        indication = row.get('asking_reference')
    source = ('Verifierade försäljningar' if row.get('market_value') is not None else
              'Begärda priser' if row.get('asking_reference') is not None else 'Saknas')
    net = (('Scenario ' if summary['evidence_kind'] == 'ACTIVE_ASKING' else '')
           + f"{summary['value']:+.0f} kr") if summary['available'] else 'Ej beräkningsbar'
    assessed = has_supported_price_context(row)
    return {'status': candidate_status(row), 'review': review, 'images': candidate_images(row),
            'price': evidence_money(indication) if indication is not None else 'Okänt',
            'source': source, 'net': net, 'summary': summary,
            'costs': acquisition_breakdown(row, row.get('total_cost')),
            'potential': f"{float(row.get('potential') or 0):.0f}/100" if assessed else 'Ej bedömd',
            'certainty': f"{float(row.get('certainty') or 0):.0f}/100" if assessed else 'Ej bedömd'}


def render_best_alternatives(result, *, explain=None, seller=None, context=None):
    import streamlit as st
    rows = result.get('rows') or []
    st.markdown('### De 5 bästa alternativen')
    if context:
        st.info(context['label'])
        if context['changed']:
            st.warning('Filtren har ändrats men sökningen har inte körts med dem. Korten nedan tillhör den sparade sökningen.')
    st.caption('En plats i listan betyder inte att kortet är ett lönsamt köp. Okänt pris betyder att relevant underlag saknas.')
    if result.get('product_scope_excluded_count'):
        st.caption(f"{result['product_scope_excluded_count']} annonser uteslutna av produktfiltret.")
    if len(rows) < 5:
        st.info(f'Endast {len(rows)} unika alternativ finns i det analyserade underlaget. Listan fylls på när fler har analyserats.')
    if not rows:
        return
    table = []
    for rank, row in enumerate(rows, 1):
        view = candidate_presentation(row)
        review = view['review']
        source_item = row.get('_source_item') or row
        with st.container(border=True):
            st.markdown(f"#### {rank}. {clean_card_title(row['title'])}")
            left, right = st.columns([1, 3], gap='medium')
            with left:
                if view['images']:
                    st.image(view['images'][0], width=220, caption='Annonsbild · kontrollera själv')
                    if len(view['images']) > 1:
                        with st.expander(f"Fler annonsbilder ({len(view['images']) - 1})"):
                            for image in view['images'][1:]:
                                st.image(image, width=220)
                    st.link_button('Förstora bild ↗', view['images'][0], key=f'candidate_image_{rank}')
                else:
                    st.caption('Annonsbild saknas i underlaget.')
            with right:
                if view['status'] == 'Köpunderlag finns':
                    st.success(view['status'] + ' · enligt sparad analys')
                elif view['status'] == 'Avstå':
                    st.warning(view['status'] + ' · enligt sparad analys')
                else:
                    st.write('**Granska** · köp ej bekräftat')
                st.write('**Total kostnad: ' + evidence_money(view['costs']['total']) + '**')
                st.caption(' · '.join(label + ' ' + evidence_money(value) for label, value in view['costs']['parts']))
                if not view['costs']['verified']:
                    st.caption('Kostnaden är ett sparat scenario. Kontrollera aktuellt pris och avgifter.')
                st.write('**Varför granska:** ' + ' · '.join(review['reasons'][:2]))
                if view['summary']['available']:
                    st.write('**' + view['summary']['label'] + ':** ' + view['net'])
                    st.caption(view['summary']['basis'])
                st.write('**Kontrollera först:** ' + review['checks'][0])
                st.write('**Prisunderlag:** ' + view['source'] + ' · prisindikation ' + view['price'])
                if row.get('url'):
                    st.link_button('Öppna annonsen ↗', row['url'], key=f'candidate_open_{rank}', use_container_width=True)
            with st.expander('Kontrollista och kortidentitet', expanded=False):
                st.write('**Kontrollera före köp:**')
                for check in review['checks']:
                    st.write('• ' + check)
                for fact in review['identity']['rows']:
                    st.write(f"**{fact['label']}:** {fact['value']} · källa: {fact['source'] or 'Saknas'}")
                st.caption(review['identity']['note'])
            render_listing_review(source_item, total_cost=row.get('total_cost'))
            with st.expander('Fördjupning och analysmått', expanded=False):
                st.write('Fyndpotential: ' + view['potential'] + ' · Analyssäkerhet: ' + view['certainty'])
                st.write(view['summary']['label'] + ': ' + view['net'])
                st.caption(view['summary']['basis'])
                if row.get('primary_blocker'):
                    st.caption('Verifieringslucka: ' + row['primary_blocker'])
                if explain:
                    explain(source_item, f'top5_{rank}')
                if seller:
                    seller(source_item, f'top5_{rank}')
        table.append({'#': rank, 'Kort': clean_card_title(row['title']), 'Bedömning': view['status'],
                      'Total kostnad': evidence_money(view['costs']['total']), 'Prisindikation': view['price'],
                      'Underlag': view['source'], 'Netto / scenario': view['net'],
                      'Fyndpotential': view['potential'], 'Säkerhet': view['certainty']})
    with st.expander('Jämför alternativen i tabell', expanded=False):
        st.dataframe(table, use_container_width=True, hide_index=True)
    more = result.get('review_candidates') or []
    if more:
        with st.expander(f'Fler potentiella kandidater ({len(more)})', expanded=False):
            st.caption('Ytterligare kort att granska. Dessa är inga bekräftade köp.')
            for rank, row in enumerate(more, 6):
                view = candidate_presentation(row)
                st.markdown(f"**{rank}. {clean_card_title(row['title'])}**")
                st.caption(view['status'] + ' · total kostnad ' + evidence_money(view['costs']['total']))
                st.caption('Varför granska: ' + ' · '.join(view['review']['reasons'][:2]))
                st.caption('Kontrollera först: ' + view['review']['checks'][0])
                if row.get('url'):
                    st.link_button('Öppna annonsen ↗', row['url'], key=f'review_candidate_{rank}', use_container_width=True)
