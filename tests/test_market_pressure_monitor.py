from src.exact_supply_history import build_snapshot
from src.market_pressure_monitor import summarize_realised_price_direction, build_market_pressure_monitor


def target():
    return {
        "player_name":"Connor McDavid",
        "player_match_confidence":"high",
        "set_name":"Upper Deck",
        "season":"2015-16",
        "card_number":"201",
        "card_identity_confidence_score":90,
        "identity_evidence_sources":{"player_name":["a","b"]},
    }


def snap(n,dt):
    return build_snapshot(target(),{"ready":True,"confirmed_exact":n,"possible":0,"wrong_card":0},observed_at=dt)


def sold(price,dt,card="201"):
    return {
        "player_name":"Connor McDavid","set_name":"Upper Deck","season":"2015-16","card_number":card,
        "identity_verified":True,"identity_evidence_source":"manual",
        "sold_verification_status":"verified","sale_evidence_type":"explicit_sold_price",
        "sold_price":float(price),"sold_at":dt,"source_platform":"eBay",
    }


def history():
    return [snap(5,"2026-09-01T10:00:00+00:00"),snap(2,"2026-09-09T10:00:00+00:00")]


def test_price_direction_needs_three_exact_sales():
    out=summarize_realised_price_direction(target(),history(),[
        sold(100,"2026-09-02T10:00:00+00:00"),sold(120,"2026-09-03T10:00:00+00:00")])
    assert out["status"]=="OTILLRÄCKLIG_PRISHISTORIK"
    assert out["direction"]=="EJ_BEDÖMBAR"


def test_price_direction_uses_exact_verified_sold_only():
    rows=[
        sold(100,"2026-09-02T10:00:00+00:00"),
        sold(120,"2026-09-05T10:00:00+00:00"),
        sold(140,"2026-09-08T10:00:00+00:00"),
        sold(999,"2026-09-08T10:00:00+00:00",card="202"),
    ]
    out=summarize_realised_price_direction(target(),history(),rows)
    assert out["status"]=="OK"
    assert out["direction"]=="HÖGRE_OBSERVERAT_SOLD_PRIS"
    assert out["early_median_sek"]==100.0
    assert out["late_median_sek"]==130.0
    assert out["creates_market_trend"] is False


def test_pressure_monitor_never_creates_signal_or_buy():
    rows=[
        sold(100,"2026-09-02T10:00:00+00:00"),
        sold(120,"2026-09-05T10:00:00+00:00"),
        sold(140,"2026-09-08T10:00:00+00:00"),
    ]
    out=build_market_pressure_monitor(target(),history(),rows)
    assert out["status"]=="TRE_SERIER_OBSERVERADE"
    assert out["supply_change"]==-3
    assert out["exact_sold_with_price_in_window"]==3
    assert out["creates_demand_signal"] is False
    assert out["creates_scarcity_score"] is False
    assert out["creates_market_trend"] is False
    assert out["creates_buy_decision"] is False
    assert out["creates_value"] is False


def test_outside_window_sale_is_ignored():
    rows=[
        sold(50,"2026-08-01T10:00:00+00:00"),
        sold(100,"2026-09-02T10:00:00+00:00"),
        sold(120,"2026-09-05T10:00:00+00:00"),
        sold(140,"2026-09-08T10:00:00+00:00"),
    ]
    out=build_market_pressure_monitor(target(),history(),rows)
    assert out["exact_sold_with_price_in_window"]==3
