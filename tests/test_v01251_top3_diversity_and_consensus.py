from src.decision_tiers import build_decision_tiers
from src.multi_source_comp_consensus import build_multi_source_consensus
from src.comp_source_intelligence import build_comp_research_plan


def _item(title, player, certainty=88, potential=21, sold=0, identity=False):
    return {
        "titel": title,
        "deal_score": potential,
        "ranking_confidence_score": certainty,
        "sold_comparable_count": sold,
        "exact_identity_gate_supports_exact_comp_search": identity,
        "exact_identity_gate_identity_fields": {"player_name": player},
        "beslut": "SKIP",
    }


def test_top3_prefers_player_diversity_when_alternatives_exist():
    rows = build_decision_tiers([
        _item("Wayne Gretzky A", "Wayne Gretzky", 88, 21),
        _item("Wayne Gretzky B", "Wayne Gretzky", 87, 20),
        _item("Wayne Gretzky C", "Wayne Gretzky", 86, 19),
        _item("Connor McDavid A", "Connor McDavid", 70, 18),
        _item("Sidney Crosby A", "Sidney Crosby", 69, 17),
    ], total_limit=3)
    players = [r["player_key"] for r in rows["rows"]]
    assert len(set(players)) == 3
    assert players.count("wayne gretzky") == 1


def test_top3_certainty_is_capped_without_identity_and_sold_comps():
    row = build_decision_tiers([_item("Wayne Gretzky A", "Wayne Gretzky", 88, 21)], total_limit=1)["rows"][0]
    assert row["raw_certainty"] == 88
    assert row["certainty"] <= 49
    assert row["certainty_limits"]


def test_comp_plan_includes_tradera_fanatics_and_comc():
    plan=build_comp_research_plan({"player_name":"Wayne Gretzky","season":"1997-98","set_name":"Collector's Choice","card_number":"167"})
    keys={r["key"] for r in plan["sources"]}
    assert {"tradera_sold","fanatics_collect","comc"}.issubset(keys)
    tradera=next(r for r in plan["sources"] if r["key"]=="tradera_sold")
    assert "tradera.com/search" in tradera["direct_query_url"]


def _sale(source, price):
    return {
        "title":"1997-98 Collector's Choice Wayne Gretzky #167",
        "player_name":"Wayne Gretzky",
        "set_name":"Collector's Choice",
        "season":"1997-98",
        "card_number":"167",
        "sold_price":price,
        "sold_price_sek":price,
        "currency":"SEK",
        "sale_status":"sold",
        "sold_verification_status":"verified",
        "source_sale_evidence":"explicit_sold_status",
        "source_platform":source,
    }


def test_multi_source_consensus_keeps_local_and_international_separate():
    identity={"player_name":"Wayne Gretzky","set_name":"Collector's Choice","season":"1997-98","card_number":"167"}
    result=build_multi_source_consensus(identity,[
        _sale("Tradera verifierade avslut",100),
        _sale("Tradera verifierade avslut",120),
        _sale("eBay",180),
        _sale("eBay",200),
    ])
    assert result["exact_sold_count"] == 4
    assert result["tradera_median_sek"] == 110
    assert result["international_median_sek"] == 190
    assert result["weighted_median_sek"] is not None
    assert result["local_vs_international_divergence_pct"] > 25


def test_price_guide_without_individual_sale_evidence_is_not_consensus_sale():
    identity={"player_name":"Wayne Gretzky","set_name":"Collector's Choice","season":"1997-98","card_number":"167"}
    guide={
        "title":"1997-98 Collector's Choice Wayne Gretzky #167",
        "player_name":"Wayne Gretzky","set_name":"Collector's Choice","season":"1997-98","card_number":"167",
        "sold_price_sek":500,"currency":"SEK","source_platform":"SportsCardsPro price guide",
        "sale_status":"sold",  # existing strict sold checker may accept this, but no individual evidence
    }
    # Because sale_status is explicit, this is considered an individual sale record.
    # A pure guide row without a sold marker must be ignored.
    guide2=dict(guide)
    guide2.pop("sale_status")
    result=build_multi_source_consensus(identity,[guide2])
    assert result["exact_sold_count"] == 0
