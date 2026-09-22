from src.analysis_budget import fast_analysis_budget


def test_small_search_analyzes_every_candidate():
    assert fast_analysis_budget(45, context="ordinary") == 45
    assert fast_analysis_budget(45, context="seller") == 45


def test_large_search_has_bounded_top_five_budget():
    assert 80 <= fast_analysis_budget(1800, context="ordinary") <= 160
    assert 60 <= fast_analysis_budget(9000, context="seller") <= 120


def test_budget_is_monotonic_until_ceiling():
    values = [fast_analysis_budget(n, context="ordinary") for n in (80, 200, 800, 8000)]
    assert values == sorted(values)
    assert values[-1] == 160


def test_main_and_seller_search_use_shared_budget_contract():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    pipeline = (root / "src" / "ordinary_analysis_pipeline_v2.py").read_text(encoding="utf-8")
    seller = (root / "src" / "seller_top5.py").read_text(encoding="utf-8")
    assert 'fast_analysis_budget(len(fast_pool_source), context="ordinary")' in pipeline
    assert 'fast_analysis_budget(len(unique_inventory), context="seller")' in seller
