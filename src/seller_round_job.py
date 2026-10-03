"""A bounded seller round that never touches a Streamlit widget/session."""
from src import resumable_search
from src.seller_proxy_inventory import fetch_proxy_seller_inventory_batch
from src.search_progress import report_phase, begin_phase


def clear_durable_search(seller, profile_url, database_url):
    """Queue remote cleanup before the next round on the same search worker."""
    if not database_url:
        return
    from src.seller_top5_controller import reset_seller_top5_search
    from src.persistent_store import save_namespace

    def clear():
        # No Streamlit state in the worker. Serial execution prevents a slow
        # old deletion from erasing checkpoints written by the next round.
        reset_seller_top5_search(seller, profile_url, database_url=database_url, session={})
        try:
            save_namespace(database_url, 'seller_last_result', None)
        except Exception:
            pass
        return [], {}

    token = resumable_search.new_token()
    resumable_search.start(token, {'kind': 'seller_reset'}, clear,
                           fresh=True)
    return token


def start(token, *, seller, profile_url, market_items, analyze_fn, credentials=None,
          checkpoint=None, registry=None, database_url=None, resolve_fn=None):
    if resolve_fn is None:
        from src.seller_top5_controller import resolve_seller_top5
        resolve_fn = resolve_seller_top5
    params = {'kind': 'seller', 'seller': seller, 'profile_url': profile_url}
    def work():
        def progress(info):
            phase = str(info.get('phase') or '')
            if phase.startswith('full_'):
                label, unit = 'Djupanalyserar kort', 'kort'
            elif phase.startswith('quick_') or phase.startswith('filter_'):
                label, unit = 'Granskar nya kort', 'kort'
            elif phase == 'pool_start':
                label, unit = 'Väljer kort för nästa analyssteg', 'kort'
            elif phase in {'ranking', 'complete'} and 'done' in info:
                label, unit = 'Uppdaterar och sparar topp 5', 'kort'
            else:
                label, unit = 'Läser säljarens annonser', 'sidor'
            if phase in {'full_start', 'quick_start', 'filter_start'}:
                begin_phase(label, info.get('total') or 0, unit=unit)
            finalizing = label in {'Uppdaterar och sparar topp 5', 'Väljer kort för nästa analyssteg'}
            report_phase(label, checked=0 if finalizing else info.get('done'),
                         total=0 if finalizing else info.get('total'),
                         unit=unit, fraction=(info.get('percent') or 0) / 100,
                         page=info.get('page'))
        result = resolve_fn(seller, market_items, analyze_fn=analyze_fn, sport='all',
                            credentials=credentials, profile_url=profile_url,
                            progress_callback=progress, quick_limit=60, full_limit=4, public_pages=1, public_attempts=1,
                            public_fetcher=fetch_proxy_seller_inventory_batch,
                            database_url=database_url, resume_checkpoint=checkpoint,
                            analysis_registry=registry or {})
        if profile_url and result.get('inventory_source') == 'LOCAL_MARKET':
            result = dict(result, status='PROFILE_INCOMPLETE', rows=[])
        report_phase('Slutför och sparar omgången', checked=0, total=0, fraction=.99)
        return [result], {}
    return resumable_search.start(token, params, work, database_url=database_url, fresh=True)


def render_status(token, database_url=None):
    """Refresh only the small status panel, rather than all results/storage."""
    import streamlit as st
    from src.search_progress import render_search_progress

    @st.fragment(run_every='1s')
    def panel():
        job = resumable_search.load(token, database_url)
        if not job:
            st.warning('Kan inte läsa sökstatus. Sparade framsteg finns kvar.')
        elif job.get('status') != 'RUNNING':
            st.rerun(scope='app')
        else:
            render_search_progress(job)
            st.caption('Högst 1 profilsida och 4 djupanalyser per omgång. Tid kvar gäller aktuellt steg.')
            st.caption('Status uppdateras varje sekund. Du kan byta fönster medan omgången fortsätter.')
    panel()
