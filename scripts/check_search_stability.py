"""Offline load check of real job, workspace and seller Top-5 state transitions.

Uses synthetic analyser outputs; makes no marketplace/API calls. Run from the
repository root with python scripts/check_search_stability.py --rounds 12 --rows 2000.
"""
import argparse
import gc
import json
from pathlib import Path
import resource
import sys
import tempfile
from threading import Event
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import resumable_search as jobs
from src import workspace_recovery as recovery
from src.seller_analysis_registry import BEST_ROW_LIMIT
from src.seller_dynamic_top5 import update_dynamic_top5, dismiss_seller_alternative, preserve_dismissals
from src.seller_top5 import _seller_alternative_rank_key, _select_diverse_rows, _refresh_collector_research


def rss_mib():
    try:
        for line in Path('/proc/self/status').read_text().splitlines():
            if line.startswith('VmRSS:'):
                return int(line.split()[1]) / 1024
    except OSError:
        pass
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def run(rounds=8, rows=1000, description_chars=4000):
    measurements, tokens = [], []
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='flipfynd-stability-') as temp:
        old_jobs_root, old_recovery_root, old_jobs = jobs._ROOT, recovery._ROOT, jobs._JOBS
        jobs._ROOT = Path(temp) / 'jobs'
        recovery._ROOT = Path(temp) / 'workspaces'
        jobs._JOBS = {}
        registry = None
        inventory = []
        seller = {}
        workspace = jobs.new_token()
        try:
            for turn in range(rounds):
                token = jobs.new_token()
                tokens.append(token)
                entered, release = Event(), Event()
                result_rows = [dict(titel=f'Card {turn}-{n}', id=f'{turn}-{n}',
                                    full_description=f'{turn}-{n}:' + 'x' * description_chars)
                               for n in range(rows)]
                def work(payload=result_rows):
                    entered.set()
                    assert release.wait(10)
                    return payload, {'final_results': len(payload), 'round': turn}
                assert jobs.start(token, {'widgets': {'search_budget': 1000}}, work, fresh=True)
                assert entered.wait(5)
                assert jobs.load(token)['status'] == 'RUNNING'
                assert not jobs.start(token, {}, work), 'Disconnect must not duplicate analysis'
                release.set()
                deadline = time.monotonic() + 30
                while jobs.load(token)['status'] == 'RUNNING' and time.monotonic() < deadline:
                    time.sleep(.01)
                completed = jobs.load(token)
                assert completed['status'] == 'COMPLETED'
                assert len(completed['results']) == rows
                assert len(jobs._JOBS) <= 2

                new_rows = []
                for n in range(12):
                    key = str(turn * 12 + n)
                    source = {'tradera_item_id': key, 'titel': f'2023-24 Upper Deck Hockey Player {key} #{key}',
                              'pris': 20, 'lank': f'https://www.tradera.com/item/293316/{key}',
                              'source_category': 'Hockey'}
                    inventory.append(source)
                    new_rows.append({'title': source['titel'], 'url': source['lank'], 'price': 20,
                                     'source_item': source, 'rank_score': int(key), 'analysis_level': 'full'})
                registry, alternatives = update_dynamic_top5(
                    registry, inventory=inventory, quick_rows=[], full_rows=new_rows, seed_rows=[],
                    rank_key=_seller_alternative_rank_key, refresh=_refresh_collector_research,
                    quick_fallback=lambda value: value, select_diverse=_select_diverse_rows)
                seller = {'seller': 'test', 'alternatives': alternatives, 'analysis_registry': registry,
                          'public_checkpoint': {'next_page': turn + 2, 'analysis_registry': registry}}
                stale_worker = seller
                hidden_key = alternatives[4]['source_item']['tradera_item_id']
                seller = dismiss_seller_alternative(seller, hidden_key)
                seller = preserve_dismissals(stale_worker, seller)
                registry = seller['analysis_registry']
                assert hidden_key not in registry['displayed_keys']
                assert len(seller['alternatives']) == 5
                assert len(registry['alternative_rows']) <= BEST_ROW_LIMIT
                state = {'results': completed['results'], 'seller_top5_result': seller,
                         'search_budget': 1000, 'search_text': 'test'}
                query = {'search_run': token}
                assert recovery.save(workspace, recovery.snapshot(state, query))
                fresh_state, fresh_query = {}, {}
                recovery.restore(fresh_state, fresh_query, recovery.load(workspace))
                assert len(fresh_state['results']) == rows
                assert fresh_state['seller_top5_result']['analysis_registry']['dismissed_keys'] == registry['dismissed_keys']
                assert fresh_query['search_run'] == token
                assert fresh_state['seller_top5_result']['public_checkpoint']['next_page'] == turn + 2
                del fresh_state, state, completed, result_rows, work
                gc.collect()
                measurements.append(round(rss_mib(), 2))
            # Simulate process loss: every older completed job remains recoverable.
            jobs._JOBS.clear()
            oldest = jobs.load(tokens[0])
            assert len(oldest['results']) == rows and oldest['debug']['round'] == 0
            del oldest
        finally:
            jobs._ROOT, recovery._ROOT, jobs._JOBS = old_jobs_root, old_recovery_root, old_jobs
            recovery._HASHES.pop(workspace, None)
    warm = measurements[min(2, len(measurements) - 1)]
    growth = max(measurements[min(2, len(measurements) - 1):]) - warm
    assert growth < 32, f'Process memory grew {growth:.2f} MiB after warm-up'
    return {'mode': 'offline_synthetic_analysis_real_state_flow', 'rounds': rounds,
            'rows_per_round': rows, 'description_chars': description_chars,
            'rss_mib_by_round': measurements, 'growth_after_warmup_mib': round(growth, 2),
            'peak_rss_mib': round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
            'duplicate_jobs': 0, 'restored_removed_cards': 0,
            'seconds': round(time.monotonic() - started, 2), 'status': 'passed'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds', type=int, default=8)
    parser.add_argument('--rows', type=int, default=1000)
    args = parser.parse_args()
    print(json.dumps(run(rounds=args.rounds, rows=args.rows), ensure_ascii=False))
