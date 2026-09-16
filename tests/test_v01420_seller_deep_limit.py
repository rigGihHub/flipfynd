from pathlib import Path

from src.adaptive_deepening import select_dynamic_seller_deep_rows


def test_seller_deep_analysis_can_select_twenty_credible_candidates():
    rows = [{"decision": "UNDERSÖK", "collector_signal_score": 20} for _ in range(30)]
    assert len(select_dynamic_seller_deep_rows(rows, base_limit=8)) == 20


def test_app_and_seller_workflow_use_release_limit():
    app = Path("app.py").read_text(encoding="utf-8")
    seller = Path("src/seller_top5.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "v0.14.29"' in app
    assert "max_cap=20" in seller
