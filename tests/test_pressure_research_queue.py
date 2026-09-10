from src.exact_supply_history import build_snapshot
from src.pressure_research_queue import build_pressure_research_row, build_pressure_research_queue


def target(card="201"):
    return {
        "player_name":"Connor McDavid",
        "player_match_confidence":"high",
        "set_name":"Upper Deck",
        "season":"2015-16",
        "card_number":card,
        "card_identity_confidence_score":90,
        "identity_evidence_sources":{"player_name":["a","b"]},
    }


def sold(price, when, card="201"):
    return {
        "player_name":"Connor McDavid",
        "set_name":"Upper Deck",
        "season":"2015-16",
        "card_number":card,
        "identity_verified":True,
        "identity_evidence_source":"manual",
        "sold_verification_status":"verified",
        "sale_evidence_type":"explicit_sold_price",
        "sold_price":float(price),
        "sold_at":when,
        "source_platform":"eBay",
    }


def snap(item, n, when):
    return build_snapshot(item,{"ready":True,"confirmed_exact":n,"possible":0,"wrong_card":0},observed_at=when)


def strong_fixture():
    item=target()
    history=[snap(item,5,"2026-09-01T10:00:00+00:00"),snap(item,2,"2026-09-09T10:00:00+00:00")]
    sales=[
        sold(100,"2026-09-02T10:00:00+00:00"),
        sold(120,"2026-09-04T10:00:00+00:00"),
        sold(180,"2026-09-08T10:00:00+00:00"),
    ]
    return item,history,sales


def test_three_observed_conditions_prioritize_research_not_buy():
    item,history,sales=strong_fixture()
    out=build_pressure_research_row(item,history,sales)
    assert out["status"]=="PRIORITERA_RESEARCH"
    assert out["evidence_count"]==3
    assert out["creates_buy_decision"] is False
    assert out["creates_value"] is False
    assert out["creates_demand_signal"] is False


def test_two_conditions_are_research_only():
    item,history,sales=strong_fixture()
    sales=[sold(100,"2026-09-02T10:00:00+00:00"),sold(100,"2026-09-04T10:00:00+00:00"),sold(100,"2026-09-08T10:00:00+00:00")]
    out=build_pressure_research_row(item,history,sales)
    assert out["status"]=="RESEARCH"
    assert out["eligible"] is True


def test_weak_pressure_not_in_queue():
    item=target()
    history=[snap(item,2,"2026-09-01T10:00:00+00:00"),snap(item,3,"2026-09-09T10:00:00+00:00")]
    out=build_pressure_research_queue([item],history,[])
    assert out["rows"]==[]
    assert out["creates_new_score"] is False


def test_queue_dedupes_exact_identity():
    item,history,sales=strong_fixture()
    duplicate=dict(item); duplicate["titel"]="Duplicate listing"
    out=build_pressure_research_queue([item,duplicate],history,sales)
    assert len(out["rows"])==1
