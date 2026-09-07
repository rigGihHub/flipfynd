from datetime import datetime,timezone
from src.comp_recency_transparency import build_comp_recency_transparency
N=datetime(2026,9,6,tzinfo=timezone.utc)
def r(p,d,i):return {"price":p,"sold_at":d,"sold_comp_id":i}
def test_profile():
 x=build_comp_recency_transparency([r(100,"2026-09-01","1"),r(110,"2026-08-01","2"),r(120,"2026-07-01","3")],now=N);assert (x["newest_age_days"],x["median_age_days"],x["oldest_age_days"])==(5,36.0,67)
def test_median_carrier():
 x=build_comp_recency_transparency([r(100,"2026-09-01","1"),r(110,"2026-01-01","2"),r(120,"2026-08-01","3")],now=N);assert x["median_carrier_ages_days"]==[248]
def test_even_carriers():
 x=build_comp_recency_transparency([r(100,"2026-09-01","1"),r(120,"2026-08-01","2")],now=N);assert len(x["median_carrier_ages_days"])==2
def test_missing():
 x=build_comp_recency_transparency([{"price":100,"sold_comp_id":"1"},r(110,"2026-08-01","2")],now=N);assert x["missing_date_count"]==1
def test_future():
 x=build_comp_recency_transparency([r(100,"2026-10-01","1"),r(110,"2026-08-01","2")],now=N);assert x["future_date_count"]==1
def test_dedupe():
 a=r(100,"2026-09-01","x");x=build_comp_recency_transparency([a,dict(a),r(110,"2026-08-01","2")],now=N);assert x["independent_count"]==2
def test_empty():assert build_comp_recency_transparency([],now=N)["status"]=="NO_EXACT_COMPS"
