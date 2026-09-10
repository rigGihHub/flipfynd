from src.exact_supply_history import build_snapshot
from src.pressure_research_drilldown import build_pressure_drilldown

def item():
    return {
        "player_name":"Connor McDavid",
        "player_match_confidence":"high",
        "set_name":"Upper Deck",
        "season":"2015-16",
        "card_number":"201",
        "card_identity_confidence_score":90,
        "identity_evidence_sources":{"player_name":["a","b"]},
        "decision":"BEVAKA",
        "sold_comparable_count":3,
        "valuation_display_safe":False,
        "valuation_confidence_score":55,
    }

def sold(price, dt):
    return {
        "player_name":"Connor McDavid",
        "set_name":"Upper Deck",
        "season":"2015-16",
        "card_number":"201",
        "identity_verified":True,
        "identity_evidence_source":"manual",
        "sold_verification_status":"verified",
        "sale_evidence_type":"explicit_sold_price",
        "sold_price":float(price),
        "sold_at":dt,
        "source_platform":"eBay",
    }

def snapshot(n, dt):
    return build_snapshot(
        item(),
        {"ready":True,"confirmed_exact":n,"possible":0,"wrong_card":0},
        observed_at=dt,
    )

def test_drilldown_explains_pressure_and_keeps_research_only():
    history=[
        snapshot(4,"2026-09-01T10:00:00+00:00"),
        snapshot(2,"2026-09-09T10:00:00+00:00"),
    ]
    solds=[
        sold(100,"2026-09-02T10:00:00+00:00"),
        sold(120,"2026-09-05T10:00:00+00:00"),
        sold(140,"2026-09-08T10:00:00+00:00"),
    ]
    out=build_pressure_drilldown(item(),history,solds)
    kinds={r["kind"] for r in out["why"]}
    assert {"SUPPLY_DOWN","VERIFIED_SOLD","PRICE_UP"} <= kinds
    assert len(out["sold_evidence"])==3
    assert out["creates_buy_decision"] is False
    assert out["creates_value"] is False
    assert out["creates_demand_signal"] is False

def test_drilldown_lists_existing_buy_blockers_without_upgrading():
    history=[
        snapshot(4,"2026-09-01T10:00:00+00:00"),
        snapshot(2,"2026-09-09T10:00:00+00:00"),
    ]
    out=build_pressure_drilldown(item(),history,[])
    text=" ".join(out["blockers_before_buy_consideration"])
    assert "Marknadsvärdet är inte säkert nog" in text
    assert "Värderingssäkerheten är för låg" in text
    assert "BEVAKA" in text
    assert out["current_decision"]=="BEVAKA"

def test_no_blockers_does_not_equal_buy():
    strong=item()
    strong.update({
        "decision":"KÖP",
        "valuation_display_safe":True,
        "valuation_confidence_score":80,
        "exact_identity_gate_supports_dynamic_max_bid":True,
        "max_item_price":100,
    })
    # Identity gate itself is still the source of truth; module never returns a new buy.
    out=build_pressure_drilldown(strong,[],[])
    assert out["creates_buy_decision"] is False
