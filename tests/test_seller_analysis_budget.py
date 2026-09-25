from src.analysis_budget import seller_deep_analysis_budget


def test_seller_deep_budget_scales_but_stays_bounded():
    assert seller_deep_analysis_budget(0) == 0
    assert seller_deep_analysis_budget(11) == 8
    assert seller_deep_analysis_budget(120) == 16
    assert seller_deep_analysis_budget(452) == 24
    assert seller_deep_analysis_budget(10_000) == 30
