from src.collector_signal_coverage import add_collector_signal_coverage_indices
from src.fast_analysis_pool import select_fast_analysis_pool


def _candidate(title, rank):
    item = {"titel": title, "lank": title}
    return item, {"rank_score": rank, "player_market_score": rank}, {}


def test_broad_fast_pool_reserves_an_autograph_slot():
    ordinary = [
        {"titel": f"Rookie parallel card {idx}", "lank": f"ordinary-{idx}", "pris": idx + 1}
        for idx in range(200)
    ]
    autograph = {"titel": "Veteran hard-signed autograph", "lank": "auto", "pris": 250}

    selected = select_fast_analysis_pool(ordinary + [autograph], cap=80, exploration_fraction=0.25)

    assert autograph in selected


def test_signal_reservations_never_exceed_the_pool_cap():
    items = [
        {"titel": "On-card autograph 1/1 patch relic SSP", "lank": f"special-{idx}"}
        for idx in range(10)
    ]

    assert len(select_fast_analysis_pool(items, cap=3, exploration_fraction=0.25)) == 3


def test_broad_search_adds_omitted_autograph_to_full_analysis():
    candidates = [_candidate(f"Ordinary card {idx}", 100 - idx) for idx in range(20)]
    candidates.append(_candidate("Low fast-rank on-card autograph", 1))

    selected, added = add_collector_signal_coverage_indices(
        candidates, list(range(12)), extra_slots=6, hard_cap=30
    )

    assert 20 in added
    assert 20 in selected
