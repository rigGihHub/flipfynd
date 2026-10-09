"""UI workflow state; does not change card evidence or purchase decisions."""
from copy import deepcopy
from src.collector_evidence import timestamp

SEARCH_WIDGETS = ('search_sport', 'search_budget', 'search_text', 'search_archive',
                  'search_sale_type', 'ordinary_card_type_filter')


def search_widgets(state):
    return {key: state.get(key) for key in SEARCH_WIDGETS}


def pending_search(state, category):
    return {'widgets': search_widgets(state), 'category': category}


def pending_phase(request, fetch_status, fetch_category):
    if not isinstance(request, dict):
        return None
    if fetch_status == 'running':
        return 'WAIT'
    if fetch_status == 'finished' and request.get('category') == fetch_category:
        return 'READY'
    return 'FAILED'


def clear_results(state, query):
    """Forget this browser's result, never the shared market or seller state."""
    state['_browser_clear_requested'] = True
    query.pop('search_run', None)
    for key in ('active_search_job_id', 'results_data_version', 'pending_find_request',
                'results_stale_notice', 'restored_completed_search'):
        state.pop(key, None)
    state['results'] = None
    state['debug'] = None
    state['result_cache'] = {}


def result_context(snapshot, current_widgets):
    widgets = deepcopy(((snapshot or {}).get('params') or {}).get('widgets') or {})
    parts = ['Sparad sökning', widgets.get('search_sport') or 'Sport ej sparad']
    budget = widgets.get('search_budget')
    if isinstance(budget, (int, float)) and not isinstance(budget, bool):
        parts.append(f'max {budget:g} kr inklusive frakt')
    text = str(widgets.get('search_text') or '').strip()
    parts.append(('sökning: ' + text if text else 'bred sökning') if widgets else 'Filter ej sparade')
    parts.append('analys klar ' + timestamp((snapshot or {}).get('completed_at')))
    changed = bool(widgets) and any(current_widgets.get(k) != v for k, v in widgets.items()
                                   if k in SEARCH_WIDGETS)
    return {'label': ' · '.join(parts), 'changed': changed, 'widgets': widgets}
