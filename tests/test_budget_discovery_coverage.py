from src.budget_discovery_coverage import add_budget_coverage_indices, budget_coverage_summary

def c(price, score, player):
    return ({"pris":price},{"rank_score":score,"player_name":player},{})

def test_budget_coverage_adds_missing_higher_price_band():
    candidates=[
        c(10,100,"A"),
        c(20,90,"B"),
        c(300,80,"C"),
        c(700,70,"D"),
    ]
    selected, added=add_budget_coverage_indices(candidates,[0,1],budget=1000,extra_slots=2,hard_cap=4)
    assert 2 in added or 3 in added
    summary=budget_coverage_summary(candidates,selected,1000)
    assert summary["mid"] + summary["upper"] >= 1

def test_does_not_change_existing_selection_or_exceed_cap():
    candidates=[c(i*100,100-i,str(i)) for i in range(1,10)]
    selected,added=add_budget_coverage_indices(candidates,[0,1,2],budget=1000,extra_slots=8,hard_cap=5)
    assert selected[:3]==[0,1,2]
    assert len(selected)<=5
