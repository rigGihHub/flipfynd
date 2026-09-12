from src.seller_bundle_opportunity import find_same_seller_listings, build_shared_shipping_scenario, classify_same_seller_addon, build_best_same_seller_basket


def test_finds_only_same_seller_and_excludes_current():
    current={"saljare":"cardswe","lank":"a","pris":100,"frakt":39}
    market=[current,{"saljare":"cardswe","lank":"b","titel":"Kort B","pris":50,"frakt":39},{"saljare":"other","lank":"c","pris":1}]
    out=find_same_seller_listings(current,market)
    assert out["count"] == 1
    assert out["rows"][0]["url"] == "b"


def test_analysed_buy_rows_rank_before_unanalysed():
    current={"saljare":"cardswe","lank":"a","pris":100}
    market=[current,{"saljare":"cardswe","lank":"b","titel":"B","pris":20},{"saljare":"cardswe","lank":"c","titel":"C","pris":10}]
    results=[{"saljare":"cardswe","lank":"b","titel":"B","pris":20,"beslut":"KÖP","fyndpotential":80}]
    out=find_same_seller_listings(current,market,results=results)
    assert out["rows"][0]["url"] == "b"
    assert out["rows"][0]["analysed"] is True


def test_shared_shipping_scenario_is_explicitly_only_a_scenario():
    current={"pris":100,"frakt":39}
    other={"source_item":{"pris":60,"frakt":39}}
    out=build_shared_shipping_scenario(current,[other])
    assert out["scenario_total"] == 199
    assert out["potential_shipping_saving"] == 39
    assert "verifieras" in out["note"]


def test_unknown_shipping_marks_partial():
    out=build_shared_shipping_scenario({"pris":100,"frakt":39}, [{"source_item":{"pris":60,"frakt":None}}])
    assert out["status"] == "PARTIAL"
    assert out["potential_shipping_saving"] is None


def test_strong_buy_can_be_recommended_as_addon():
    out=classify_same_seller_addon({"analysed":True,"decision":"KÖP","identity_ok":True,"sold_comps":2,"potential":71})
    assert out["status"] == "ADD"

def test_unanalysed_card_is_never_auto_add():
    out=classify_same_seller_addon({"analysed":False,"potential":99})
    assert out["status"] == "REVIEW"

def test_weak_card_is_skipped_even_with_shared_shipping_context():
    out=classify_same_seller_addon({"analysed":True,"decision":"SKIP","identity_ok":False,"sold_comps":0,"potential":25})
    assert out["status"] == "SKIP"


def _strong(title, price, shipping, potential, sold=2):
    return {
        "title": title, "price": price, "shipping": shipping, "analysed": True,
        "decision": "KÖP", "identity_ok": True, "sold_comps": sold,
        "potential": potential, "source_item": {"pris": price, "frakt": shipping},
    }

def test_best_basket_stays_within_budget_and_prefers_stronger_cards():
    current={"pris":100,"frakt":39}
    rows=[_strong("A",100,39,80), _strong("B",80,39,70), _strong("C",300,39,99)]
    out=build_best_same_seller_basket(current, rows, 330)
    assert out["status"] == "FOUND"
    assert out["scenario_total"] <= 330
    titles=[r["title"] for r in out["selected"]]
    assert titles == ["A", "B"]

def test_best_basket_never_auto_adds_review_or_skip_rows():
    current={"pris":100,"frakt":39}
    weak={"title":"Weak","price":10,"shipping":39,"analysed":False,"potential":99,"source_item":{"pris":10,"frakt":39}}
    out=build_best_same_seller_basket(current,[weak],500)
    assert out["status"] == "NO_ELIGIBLE_ADDONS"

def test_best_basket_excludes_unknown_shipping_to_preserve_budget_truth():
    current={"pris":100,"frakt":39}
    row=_strong("Unknown ship",20,None,95)
    out=build_best_same_seller_basket(current,[row],500)
    assert out["status"] == "NO_ELIGIBLE_ADDONS"
    assert out["excluded_unknown_shipping"] == 1
