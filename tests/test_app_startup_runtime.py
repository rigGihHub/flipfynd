"""Exercise the Streamlit entrypoint, including an older loaded seller module."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src import seller_top5


@pytest.mark.parametrize("older_seller_module", [False, True])
def test_app_starts_with_current_or_older_seller_module(monkeypatch, older_seller_module):
    if older_seller_module:
        # v0.14.30 exports the builder and tier but not the v0.14.31 badge helper.
        monkeypatch.delattr(seller_top5, "seller_result_badge")
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=30).run()
    assert not app.exception, [error.message for error in app.exception]


@pytest.mark.parametrize("risk,expected_badge", [(35, "🟢 KÖP"), (90, "🟡 Värt att undersöka")])
def test_seller_badge_renders_without_new_module_export(monkeypatch, risk, expected_badge):
    monkeypatch.delattr(seller_top5, "seller_result_badge")
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=30)
    app.session_state["seller_top5_result"] = {
        "status": "OK", "seller": "test-seller", "inventory_count": 1,
        "rows": [{
            "title": "Connor McDavid Young Guns", "price": 100,
            "decision": "KÖP", "risk_score": risk, "identity_ok": True,
            "sold_comps": 3, "valuation_confidence": 80,
            "analysis_level": "full",
        }],
    }
    app.run()
    assert not app.exception, [error.message for error in app.exception]
    rendered = "\n".join(element.value for element in app.markdown)
    assert expected_badge in rendered
    if risk > 65:
        assert "🟢 KÖP" not in rendered
