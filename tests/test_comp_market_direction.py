from src.comp_market_direction import build_comp_market_direction

def r(price,date,ident): return {"price":price,"sold_at":date,"sold_comp_id":ident}

def test_all_down():
    x=build_comp_market_direction([r(420,"2026-06-01","1"),r(350,"2026-07-01","2"),r(330,"2026-08-01","3"),r(310,"2026-09-01","4")])
    assert x["direction"]=="DOWN" and x["down_moves"]==3 and x["latest_price"]==310

def test_all_up():
    x=build_comp_market_direction([r(100,"2026-06-01","1"),r(120,"2026-07-01","2"),r(150,"2026-08-01","3")])
    assert x["direction"]=="UP" and x["up_moves"]==2

def test_mixed_not_forced():
    x=build_comp_market_direction([r(100,"2026-06-01","1"),r(120,"2026-07-01","2"),r(110,"2026-08-01","3")])
    assert x["direction"]=="MIXED"

def test_recent_median_last_three():
    x=build_comp_market_direction([r(500,"2026-01-01","1"),r(300,"2026-06-01","2"),r(280,"2026-07-01","3"),r(260,"2026-08-01","4")])
    assert x["recent_prices"]==[300.0,280.0,260.0] and x["recent_median"]==280.0

def test_missing_date_excluded():
    x=build_comp_market_direction([{"price":100,"sold_comp_id":"1"},r(110,"2026-07-01","2"),r(120,"2026-08-01","3")])
    assert x["missing_date_count"]==1 and x["count"]==2

def test_duplicates_collapsed():
    a=r(100,"2026-06-01","same")
    x=build_comp_market_direction([a,dict(a),r(120,"2026-07-01","2")])
    assert x["count"]==2

def test_one_comp_abstains():
    assert build_comp_market_direction([r(100,"2026-06-01","1")])["status"]=="INSUFFICIENT_DATA"
