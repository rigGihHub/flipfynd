from src.market_direction_evidence import build_market_direction_evidence
def r(p,d,i): return {"price":p,"sold_at":d,"sold_comp_id":i}
def test_two_sales_no_score():
 x=build_market_direction_evidence([r(100,"2026-01-01","1"),r(120,"2026-06-01","2")]); assert x["exact_count"]==2 and "score" not in x
def test_unanimous():
 x=build_market_direction_evidence([r(100,"2026-06-01","1"),r(110,"2026-06-08","2"),r(120,"2026-06-15","3")]); assert x["unanimous_direction"] is True and x["dominant_move_share"]==1.0
def test_mixed():
 x=build_market_direction_evidence([r(100,"2026-06-01","1"),r(120,"2026-06-08","2"),r(110,"2026-06-15","3")]); assert x["dominant_move_share"]==0.5
def test_span():
 x=build_market_direction_evidence([r(100,"2026-06-01","1"),r(120,"2026-06-22","2")]); assert x["span_days"]==21
def test_missing_reduces_coverage():
 x=build_market_direction_evidence([{"price":90,"sold_comp_id":"x"},r(100,"2026-06-01","1"),r(120,"2026-06-22","2")]); assert x["dated_priced_coverage"]<1
def test_insufficient(): assert build_market_direction_evidence([r(100,"2026-06-01","1")])["status"]=="INSUFFICIENT_DATA"
