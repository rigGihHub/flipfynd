from pathlib import Path

def test_exact_supply_history_path_is_defined_before_runtime_use():
    app = Path(__file__).resolve().parents[1] / "app.py"
    source = app.read_text(encoding="utf-8")
    definition = 'EXACT_SUPPLY_HISTORY_PATH = BASE_DIR / "data" / "exact_supply_history.json"'
    assert definition in source
    assert source.index(definition) < source.index("load_history(EXACT_SUPPLY_HISTORY_PATH)")
