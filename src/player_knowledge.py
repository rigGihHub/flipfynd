"""Source-backed Player Knowledge Base."""
from __future__ import annotations
import json
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

DATA_FILE=Path(__file__).resolve().parents[1]/"data"/"player_knowledge.json"

@lru_cache(maxsize=1)
def load_player_knowledge():
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"hockey":{},"football":{},"policy":"Unavailable"}

def get_player_knowledge(name, sport):
    bucket="football" if sport=="football" else "hockey"
    raw=load_player_knowledge().get(bucket,{}).get(str(name or ""),{})
    out=dict(raw)
    out["verified"]=bool(raw)
    return out

def age_on(date_of_birth, on_date=None):
    if not date_of_birth:
        return None
    try:
        born=datetime.strptime(str(date_of_birth),"%Y-%m-%d").date()
    except ValueError:
        return None
    today=on_date or date.today()
    return today.year-born.year-((today.month,today.day)<(born.month,born.day))

def derive_lifecycle_context(knowledge, on_date=None):
    k=dict(knowledge or {})
    if not k.get("verified"):
        return {"stage":"unknown","label":"Okänd livscykel","age":None,"derived":False}
    activity=k.get("activity_status")
    age=age_on(k.get("date_of_birth"),on_date=on_date)
    if activity=="retired":
        stage,label="retired","Pensionerad"
    elif activity=="active" and age is not None and age<=23:
        stage,label="young_active","Ung aktiv spelare"
    elif activity=="active" and age is not None and age>=35:
        stage,label="late_career_active","Sen aktiv karriärfas"
    elif activity=="active":
        stage,label="active","Aktiv spelare"
    else:
        stage,label="unknown","Okänd livscykel"
    return {"stage":stage,"label":label,"age":age,"derived":True}

def knowledge_coverage(player_market_data):
    kb=load_player_knowledge()
    out={}
    for sport in ("hockey","football"):
        known=set((player_market_data or {}).get(sport,{}))
        covered=set(kb.get(sport,{}))
        hits=len(known & covered)
        out[sport]={
            "known_players":len(known),
            "covered_players":hits,
            "coverage_pct":round((hits/len(known)*100),1) if known else 0.0,
        }
    return out
