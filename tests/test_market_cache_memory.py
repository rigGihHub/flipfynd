"""Exercise the real market cache across repeated listing-file revisions."""
import ast
from pathlib import Path
import streamlit as st


def test_market_cache_evicts_old_versions_and_keeps_latest_data():
    app = Path(__file__).resolve().parents[1] / 'app.py'
    tree = ast.parse(app.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'get_data')
    calls = []
    revision = [0]
    def load(path):
        if path == 'market':
            calls.append(revision[0])
            return [{'id': revision[0], 'tradera_item_id': str(revision[0])}]
        return []
    namespace = {'st': st, 'load_data': load, 'DATA_PATH': 'market',
                 'SEARCH_EXPANSION_DATA_PATH': 'expansion', 'DATABASE_URL': None}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(app), 'exec'), namespace)
    cached = namespace['get_data']
    cached.clear()
    try:
        for version in range(10):
            revision[0] = version
            assert cached(version)[0]['id'] == version
            assert cached(version)[0]['id'] == version
        assert calls == list(range(10)), 'Repeated reads of the current revision must reuse it'
        cached(0)
        assert len(calls) == 11, 'Old inventory versions must be evicted instead of accumulating in memory'
    finally:
        cached.clear()
