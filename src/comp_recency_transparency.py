"""Descriptive age profile for independent Exact sold comps."""
from datetime import datetime,timezone
from statistics import median
from src.comp_set_consistency import collapse_independent_observations
def _n(v):
 try: x=float(v); return x if x>0 else None
 except (TypeError,ValueError): return None
def _d(v):
 if v in (None,""): return None
 s=str(v).strip()
 for x in (s,s.replace("Z","+00:00")):
  try:
   d=datetime.fromisoformat(x)
   if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
   return d.astimezone(timezone.utc)
  except ValueError: pass
 return None
def build_comp_recency_transparency(rows,*,now=None):
 rows=collapse_independent_observations(rows)["rows"]; now=now or datetime.now(timezone.utc)
 obs=[]; missing=0; future=0
 for r in rows:
  p=_n(r.get("price") if r.get("price") not in (None,"") else r.get("sold_price")); d=_d(r.get("sold_at") or r.get("sold_date") or r.get("date"))
  if not d: missing+=1; continue
  age=(now-d).days
  if age<0: future+=1; continue
  obs.append({"age_days":age,"price":p,"date":d.date().isoformat()})
 ages=[x["age_days"] for x in obs]; priced=[x for x in obs if x["price"] is not None]
 allp=[_n(r.get("price") if r.get("price") not in (None,"") else r.get("sold_price")) for r in rows]; allp=[x for x in allp if x]
 med=median(allp) if allp else None; carriers=[]
 if priced:
  o=sorted(priced,key=lambda x:(x["price"],x["date"])); n=len(o); ix=[n//2] if n%2 else [n//2-1,n//2]; carriers=[o[i] for i in ix]
 status="NO_EXACT_COMPS" if not rows else ("NO_VALID_DATES" if not obs else "DESCRIBED")
 return {"status":status,"independent_count":len(rows),"dated_count":len(obs),"missing_date_count":missing,"future_date_count":future,
 "newest_age_days":min(ages) if ages else None,"oldest_age_days":max(ages) if ages else None,"median_age_days":round(float(median(ages)),1) if ages else None,
 "overall_median_price":round(float(med),2) if med is not None else None,"median_carrier_ages_days":[x["age_days"] for x in carriers],
 "median_carrier_dates":[x["date"] for x in carriers],"median_carrier_prices":[round(float(x["price"]),2) for x in carriers],
 "note":"Transparenslager; inga tidsvikter eller prisjusteringar."}
