from src.premium_comp_hunter import build_premium_query, hunt_premium_comps


def target(**overrides):
    base = {
        "player_name": "Lucas Bergvall",
        "set_name": "Topps Finest",
        "season": "2024-25",
        "card_number": "RA-LB",
        "is_auto": True,
    }
    base.update(overrides)
    return base


def sold(title, price=500):
    return {"title": title, "market_state": "sold", "price": price, "sold_price": price, "sold_verification_status": "verified", "sale_evidence_type": "explicit_sold_price", "platform": "manual"}


def test_broad_base_card_is_not_exact_premium_comp():
    result = hunt_premium_comps(target(), [sold("2024-25 Topps Finest Lucas Bergvall #RA-LB")])
    assert result["exact_count"] == 0
    assert result["safe_for_valuation"] is False


def test_two_matching_autographs_unlock_premium_evidence():
    comps = [
        sold("Lucas Bergvall 2024-25 Topps Finest Autograph #RA-LB", 550),
        sold("2024-25 Topps Finest Lucas Bergvall Auto #RA-LB", 610),
    ]
    result = hunt_premium_comps(target(), comps)
    assert result["exact_count"] == 2
    assert result["safe_for_valuation"] is True


def test_parallel_must_match_when_known():
    features = target(parallel="Gold", serial_number=50)
    comps = [sold("Lucas Bergvall 2024-25 Topps Finest Gold Auto #RA-LB /50", 900),
             sold("Lucas Bergvall 2024-25 Topps Finest Blue Auto #RA-LB /150", 450)]
    result = hunt_premium_comps(features, comps)
    assert result["exact_count"] == 1
    assert result["safe_for_valuation"] is False


def test_query_contains_premium_identity_fields():
    q = build_premium_query(target(parallel="Gold", serial_number=50))
    assert "Lucas Bergvall" in q
    assert "Topps Finest" in q
    assert "#RA-LB" in q
    assert "Gold" in q
    assert "autograph" in q
    assert "/50" in q


def test_no_price_is_created_by_hunter():
    result = hunt_premium_comps(target(), [])
    forbidden = {"estimated_value", "market_value", "max_bid", "profit", "roi"}
    assert forbidden.isdisjoint(result.keys())


def test_unverified_sold_marker_is_not_a_comp():
    row={"title":"Lucas Bergvall 2024-25 Topps Finest Autograph #RA-LB","market_state":"sold","price":550}
    result=hunt_premium_comps(target(),[row])
    assert result["exact_count"]==0
    assert result["safe_for_valuation"] is False


def test_missing_season_is_not_exact_premium():
    row=sold("Lucas Bergvall Topps Finest Autograph #RA-LB",550)
    result=hunt_premium_comps(target(),[row])
    assert result["exact_count"]==0

def test_graded_comp_is_not_exact_for_raw_target():
    row=sold("Lucas Bergvall 2024-25 Topps Finest Autograph #RA-LB PSA 10",700)
    result=hunt_premium_comps(target(),[row])
    assert result["exact_count"]==0
