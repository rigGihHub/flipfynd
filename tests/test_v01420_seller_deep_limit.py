from pathlib import Path
import re

from src.adaptive_deepening import select_dynamic_seller_deep_rows


def test_seller_deep_analysis_can_select_twenty_credible_candidates():
    rows = [{"decision": "UNDERSÖK", "collector_signal_score": 20} for _ in range(30)]
    assert len(select_dynamic_seller_deep_rows(rows, base_limit=8)) == 20


def test_app_and_seller_workflow_use_release_limit():
    app = Path("app.py").read_text(encoding="utf-8")
    seller = Path("src/seller_top5.py").read_text(encoding="utf-8")
    assert re.search(r'APP_VERSION = "v0\.14\.\d+"', app)
    assert "SELLER_DEEP_ANALYSIS_CAP = 30" in seller


def test_seller_ui_has_app_local_fail_closed_money_guard():
    app = Path("app.py").read_text(encoding="utf-8")

    assert 'SELLER_PRESENTATION_CONTRACT = "positive-price-nonnegative-profit-v2"' in app
    assert "def _seller_ui_row_is_safe(row):" in app
    assert "_seller_ui_row_is_safe(row)" in app
    assert "float(value) < 0" in app
