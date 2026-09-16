from src.asking_price_ui import _net_roi, _shortlist_rank


def test_net_roi_uses_complete_acquisition_cost():
    assert _net_roi({"total_cost": 40, "net_margin": 20}) == 50
    assert _net_roi({"total_cost": 0, "net_margin": 20}) is None


def test_shortlist_keeps_absolute_profit_primary_and_roi_as_tiebreaker():
    bigger_profit = {"asking_price_opportunity": {"total_cost": 200, "net_margin": 40}}
    smaller_profit = {"asking_price_opportunity": {"total_cost": 20, "net_margin": 30}}
    assert _shortlist_rank(bigger_profit) > _shortlist_rank(smaller_profit)

    efficient = {"asking_price_opportunity": {"total_cost": 50, "net_margin": 40}}
    inefficient = {"asking_price_opportunity": {"total_cost": 200, "net_margin": 40}}
    assert _shortlist_rank(efficient) > _shortlist_rank(inefficient)
