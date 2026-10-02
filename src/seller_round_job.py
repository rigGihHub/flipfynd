"""A bounded seller round that never touches a Streamlit widget/session."""
from src import resumable_search
from src.search_progress import report_phase


def start(token, *, seller, profile_url, market_items, analyze_fn, credentials=None,
          checkpoint=None, registry=None, database_url=None, resolve_fn=None):
    if resolve_fn is None:
        from src.seller_top5_controller import resolve_seller_top5
        resolve_fn = resolve_seller_top5
    params = {'kind': 'seller', 'seller': seller, 'profile_url': profile_url}
    def work():
        def progress(info):
            phase = str(info.get('phase') or 'Söker säljaren')
            label = {'starting': 'Förbereder säljsökning', 'fetching': 'Läser säljarens annonser',
                     'full_progress': 'Djupanalyserar kort', 'quick_progress': 'Granskar nya kort',
                     'ranking': 'Uppdaterar topp 5'}.get(phase, 'Söker säljarens bästa kort')
            report_phase(label,
                         checked=info.get('done'), total=info.get('total'))
        result = resolve_fn(seller, market_items, analyze_fn=analyze_fn, sport='all',
                            credentials=credentials, profile_url=profile_url,
                            progress_callback=progress, quick_limit=60, full_limit=8,
                            database_url=database_url, resume_checkpoint=checkpoint,
                            analysis_registry=registry or {})
        if profile_url and result.get('inventory_source') == 'LOCAL_MARKET':
            result = dict(result, status='PROFILE_INCOMPLETE', rows=[])
        return [result], {}
    return resumable_search.start(token, params, work, database_url=database_url)
