"""Finish bounded research for visible candidates; never manufactures SOLD/BUY."""
from src.analysis_scope import _listing_key
from src.best_alternatives import build_best_alternatives
from src.description_price_identity import enrich_description_routes
from src.asking_price_opportunity import asking_research_identity, attach_asking_price_opportunity
from src.search_progress import begin_phase, report_phase


def research_report(row):
    identity = asking_research_identity(row)
    missing = [name for name, value in (
        ('spelare', identity.get('player_name')), ('serie', identity.get('set_name')),
        ('år', identity.get('season') or identity.get('year')),
        ('kortnummer', identity.get('card_number')),
    ) if not value]
    scenario = row.get('asking_price_opportunity') or {}
    count = int(scenario.get('comparison_count') or 0)
    if row.get('listing_inactive'):
        status, text = 'ENDED', 'Annonsen är avslutad eller ersatt.'
    elif row.get('identity_conflicts') or row.get('detail_evidence_fusion_has_conflict'):
        status, text = 'IDENTITY_CONFLICT', 'Motstridiga kortuppgifter; prisjämförelsen behöver kontrolleras på nytt.'
    elif row.get('valuation_display_safe') and int(row.get('sold_comparable_count') or row.get('sold_comps') or 0) >= 2:
        status, text = 'SOLD_CONTEXT', 'Verifierade sålda jämförelser finns enligt den sparade analysen.'
    elif missing:
        status, text = 'IDENTITY_MISSING', 'Saknar ' + ', '.join(missing) + '; exakta priser kan inte bekräftas.'
    elif scenario.get('http_status') in {401, 403, 429}:
        status, text = 'API_PAUSED', 'Prisresearch pausad av prisdatakällan. Försök igen senare.'
    elif count >= 2:
        status, text = 'ACTIVE_CONTEXT', f'{count} matchande begärda priser; försäljningsvärdet är ännu inte verifierat.'
    elif count == 1:
        status, text = 'SINGLE_PRICE', 'Ett matchande begärt pris; fler jämförelser behövs.'
    elif scenario.get('status', '').startswith('COMPARISON_'):
        status, text = 'UNAVAILABLE', 'Prisdatakällan kunde inte kontrolleras. Underlaget är ofullständigt.'
    elif scenario.get('comparison_failure_reason') == 'NO_CONVERTIBLE_PRICE_OR_FX':
        status, text = 'PRICE_OR_FX_MISSING', 'Kortjämförelser finns, men användbart pris eller aktuell valutakurs saknas.'
    elif scenario:
        status, text = 'NO_MATCH', 'Sökningen gav inga användbara exakta prisjämförelser.'
    else:
        status, text = 'NOT_CHECKED', 'Prisresearch är ännu inte genomförd för detta kort.'
    return {'status': status, 'text': text, 'missing': missing, 'comparison_count': count}


def complete_priority_research(results, *, limit=5, verifier=None, enrich=None, previously_checked=()):
    """Use at most five primary detail checks plus the existing exact price lookup.

    A single-price lead gets another identity/query attempt, but API failures
    stop the lane. Full analyses and their CPU cache are never mutated here.
    """
    enrich = enrich or attach_asking_price_opportunity
    ranked = build_best_alternatives(results)['rows']
    selected = [dict(row['_source_item']) for row in ranked
                if row.get('market_value') is None
                and row.get('decision') != 'AVSTÅ'
                and int(row.get('asking_comparison_count') or 0) < 2][:max(0, min(5, limit))]
    debug = {'priority_research_selected': len(selected), 'priority_research_checked': 0,
             'priority_research_usable': 0, 'priority_research_api_paused': False}
    if any((row.get('asking_price_opportunity') or {}).get('http_status') in {401, 403, 429}
           for row in results):
        debug['priority_research_api_paused'] = True
        return results, debug
    details = enrich_description_routes(selected, limit=5, verifier=verifier,
        previously_checked=previously_checked, priority=True)
    debug['priority_description_checked'] = details['description_identity_checked']
    debug['priority_description_fingerprints'] = details['description_checked_fingerprints']
    replacements = {}
    phase = 'Slutför prisresearch för toppkandidater'
    begin_phase(phase, len(selected))
    for row in selected:
        # Late primary detail can reveal a conflict after CPU analysis. Check
        # literal title/body identity again without promoting any valuation.
        if row.get('purchase_detail_verified') and row.get('purchase_detail_url') == row.get('lank', row.get('url')):
            from src.analyzer import get_listing_features
            sport = 'football' if 'fotboll' in str(row.get('source_category') or '').casefold() else 'hockey'
            conflicts = get_listing_features(row, sport).get('identity_conflicts') or []
            row['identity_conflicts'] = list(dict.fromkeys([*(row.get('identity_conflicts') or []), *conflicts]))
        if not row.get('listing_inactive') and not row.get('identity_conflicts') and not row.get('detail_evidence_fusion_has_conflict'):
            row = enrich(row)
        row['candidate_research_report'] = research_report(row)
        replacements[_listing_key(row)] = row
        debug['priority_research_checked'] += 1
        debug['priority_research_usable'] += row['candidate_research_report']['status'] == 'ACTIVE_CONTEXT'
        report_phase(phase, checked=debug['priority_research_checked'], total=len(selected))
        if (row.get('asking_price_opportunity') or {}).get('http_status') in {401, 403, 429}:
            debug['priority_research_api_paused'] = True
            break
    updated = [replacements.get(_listing_key(row), row) for row in results]
    return [row for row in updated if not row.get('listing_inactive')], debug
