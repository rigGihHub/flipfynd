from pathlib import Path
import re


def test_seller_search_reuses_fast_and_full_analysis_caches():
    app = Path("app.py").read_text(encoding="utf-8")

    assert "def _cached_seller_analysis" in app
    assert "_cached_fast_analysis(" in app
    assert 'mode=f"seller_v5_pricing_truth_{sport}_{strategy_mode}"' in app
    assert app.count("analyze_fn=_cached_seller_analysis") >= 2
    assert re.search(r'APP_VERSION = "v0\.14\.\d+"', app)
