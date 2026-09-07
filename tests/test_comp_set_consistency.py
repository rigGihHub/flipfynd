from src.comp_set_consistency import collapse_independent_observations
from src.comp_quality_guard import build_comp_quality_guard
from datetime import datetime, timezone

NOW=datetime(2026,9,6,tzinfo=timezone.utc)

def base(**extra):
    row={
        "player_name":"Connor Bedard","season":"2023-24","set_name":"Upper Deck Series 2",
        "card_number":"451","parallel":"Outburst","sold_at":"2026-08-15",
        "price":500,"saljare":"seller1","titel":"Connor Bedard 451 Outburst",
    }
    row.update(extra)
    return row

def test_same_url_collapses():
    r=collapse_independent_observations([base(lank="https://x.test/item/1"),base(lank="https://x.test/item/1",source_platform="mirror")])
    assert r["independent_count"]==1
    assert r["duplicate_count"]==1

def test_same_explicit_sale_id_collapses():
    r=collapse_independent_observations([base(external_sale_id="ABC"),base(external_sale_id="abc",price=510)])
    assert r["independent_count"]==1

def test_price_and_date_alone_do_not_collapse():
    a=base(saljare="",titel="")
    b=base(saljare="",titel="")
    r=collapse_independent_observations([a,b])
    assert r["independent_count"]==2

def test_high_confidence_mirror_signature_collapses():
    a=base(source_platform="ebay")
    b=base(source_platform="130point")
    r=collapse_independent_observations([a,b])
    assert r["independent_count"]==1

def test_different_seller_keeps_independent():
    r=collapse_independent_observations([base(saljare="seller1"),base(saljare="seller2")])
    assert r["independent_count"]==2

def test_different_price_keeps_independent():
    r=collapse_independent_observations([base(price=500),base(price=525)])
    assert r["independent_count"]==2

def test_quality_guard_counts_independent_sales_not_rows():
    rows=[
        base(lank="https://x.test/item/1",price=500),
        base(lank="https://x.test/item/1",price=500,source_platform="mirror"),
        base(lank="https://x.test/item/2",price=510,saljare="seller2"),
    ]
    r=build_comp_quality_guard(rows,now=NOW)
    assert r["raw_exact_count"]==3
    assert r["independent_exact_count"]==2
    assert r["status"]=="THIN"
    assert r["decision_grade"] is False

def test_duplicate_warning_is_visible():
    rows=[base(lank="https://x.test/item/1"),base(lank="https://x.test/item/1"),base(lank="https://x.test/item/2",saljare="seller2")]
    r=build_comp_quality_guard(rows,now=NOW)
    assert any("kollapsades" in w for w in r["warnings"])
