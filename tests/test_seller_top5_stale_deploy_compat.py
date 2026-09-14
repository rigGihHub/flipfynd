import importlib.util
import sys
import types
from pathlib import Path


def test_seller_top5_fallback_imports_with_older_seller_identity(monkeypatch):
    """A mixed Streamlit deploy must not crash if backfill helper is missing."""
    fake_identity = types.ModuleType("src.seller_identity")

    def seller_alias(item):
        item = item or {}
        return item.get("seller_alias") or item.get("saljare")

    fake_identity.seller_alias = seller_alias
    monkeypatch.setitem(sys.modules, "src.seller_identity", fake_identity)

    module_path = Path(__file__).resolve().parents[1] / "src" / "seller_top5_fallback.py"
    spec = importlib.util.spec_from_file_location("_seller_top5_fallback_stale_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    rows = module.local_inventory_for_seller(
        "Etanol71",
        [
            {"seller_alias": "Etanol71", "title": "Card A"},
            {"seller_alias": "OtherSeller", "title": "Card B"},
        ],
    )
    assert len(rows) == 1
    assert rows[0]["title"] == "Card A"
