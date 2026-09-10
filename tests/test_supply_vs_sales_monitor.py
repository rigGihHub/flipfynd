from src.exact_supply_history import build_snapshot
from src.supply_vs_sales_monitor import exact_verified_sold_matches, build_supply_vs_sales_monitor

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

def sold(card="201", sold_at="2026-09-05T10:00:00+00:00"):
    return {
        "player_name":"Connor McDavid",
        "set_name":"Upper Deck",
        "season":"2015-16",
        "card_number":card,
        "identity_verified":True,
        "identity_evidence_source":"manual",
        "sold_verification_status":"verified",
        "sale_evidence_type":"explicit_sold_price",
        "sold_price":100.0,
        "sold_at":sold_at,
        "source_platform":"eBay",
    }

def snapshot(n, dt):
    return build_snapshot(
        target(),
        {"ready":True,"confirmed_exact":n,"possible":0,"wrong_card":0},
        observed_at=dt,
    )

def test_only_verified_exact_sold_matches_count():
    bad=sold(); bad["identity_verified"]=False
    matches=exact_verified_sold_matches(target(),[sold(), sold("202"), bad])
    assert len(matches)==1

def test_supply_down_plus_sales_is_descriptive_only():
    history=[
        snapshot(4,"2026-09-01T10:00:00+00:00"),
        snapshot(2,"2026-09-09T10:00:00+00:00"),
    ]
    out=build_supply_vs_sales_monitor(target(),history,[sold()])
    assert out["status"]=="DESKRIPTIV_JÄMFÖRELSE"
    assert out["supply_change"]==-2
    assert out["verified_exact_sold_in_window"]==1
    assert "minskade samtidigt" in out["observation"]
    assert out["creates_demand_signal"] is False
    assert out["creates_scarcity_score"] is False
    assert out["creates_buy_decision"] is False
    assert out["creates_value"] is False

def test_active_supply_history_without_two_snapshots_fails_closed():
    out=build_supply_vs_sales_monitor(
        target(),
        [snapshot(2,"2026-09-01T10:00:00+00:00")],
        [sold()],
    )
    assert out["status"]=="OTILLRÄCKLIG_HISTORIK"
    assert out["verified_exact_sold_in_window"] is None

def test_sale_outside_supply_window_not_counted_in_window():
    history=[
        snapshot(4,"2026-09-01T10:00:00+00:00"),
        snapshot(2,"2026-09-09T10:00:00+00:00"),
    ]
    out=build_supply_vs_sales_monitor(target(),history,[sold(sold_at="2026-08-01T10:00:00+00:00")])
    assert out["verified_exact_sold_in_window"]==0
    assert out["verified_exact_sold_total"]==1
