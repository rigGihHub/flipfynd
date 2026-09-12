"""Evidence-aware comp-source planning for FlipFynd.

The key distinction is deliberate: a realised-sale database can provide direct
sale evidence, while a price guide can only provide secondary market context.
No external web UI is treated as an API unless a verified connector exists.
"""
from __future__ import annotations

from urllib.parse import quote_plus


SOURCE_PROFILES = {
    "tradera_sold": {
        "label": "Tradera verifierade avslut",
        "evidence_class": "DIRECT_REALIZED_SALES",
        "priority": 3,
        "history": "beror på tillgängliga avslut/export",
        "best_offer_actual": None,
        "use_for": "Svensk lokal prisbild och faktisk efterfrågan. Endast explicit sålda avslut räknas som comps.",
        "valuation_role": "PRIMARY_LOCAL_MARKET_WHEN_EXACT_IDENTITY_VERIFIED",
    },
    "ebay_product_research": {
        "label": "eBay Product Research",
        "evidence_class": "DIRECT_REALIZED_SALES",
        "priority": 1,
        "history": "upp till 3 år",
        "best_offer_actual": True,
        "use_for": "Verifiera verkliga försäljningar, accepted Best Offer, datum och prisintervall.",
        "valuation_role": "PRIMARY_WHEN_EXACT_IDENTITY_VERIFIED",
    },
    "ebay_sold_search": {
        "label": "eBay Sold/Completed",
        "evidence_class": "DIRECT_REALIZED_SALES",
        "priority": 2,
        "history": "senaste avslutade perioden (typiskt omkring 90 dagar)",
        "best_offer_actual": False,
        "use_for": "Snabb kontroll av färska avslut och länkar till enskilda objekt.",
        "valuation_role": "PRIMARY_WHEN_PRICE_IS_ACTUAL_AND_IDENTITY_VERIFIED",
    },
    "card_ladder": {
        "label": "Card Ladder",
        "evidence_class": "MULTI_MARKET_SALES_DATABASE",
        "priority": 4,
        "history": "bred historik; tjänsten uppger offentliga försäljningar tillbaka till 2000",
        "best_offer_actual": None,
        "use_for": "Korsmarknadskontroll, äldre försäljningar och tunna marknader.",
        "valuation_role": "PRIMARY_IF_INDIVIDUAL_SALE_IS_VERIFIABLE",
    },
    "fanatics_collect": {
        "label": "Fanatics Collect Sales History",
        "evidence_class": "DIRECT_REALIZED_SALES",
        "priority": 5,
        "history": "publik sales history enligt tjänstens tillgängliga historik",
        "best_offer_actual": None,
        "use_for": "Verifiera individuella realiserade försäljningar från Fanatics Collect.",
        "valuation_role": "PRIMARY_IF_INDIVIDUAL_SALE_IS_VERIFIABLE",
    },
    "comc": {
        "label": "COMC",
        "evidence_class": "MARKETPLACE_SALES_DATABASE",
        "priority": 6,
        "history": "tjänsten visar historisk försäljnings-/prisdata där tillgängligt",
        "best_offer_actual": None,
        "use_for": "Sekundär marknadskontroll och individuella sales när exakt kort och realiserat pris kan verifieras.",
        "valuation_role": "PRIMARY_IF_INDIVIDUAL_SALE_IS_VERIFIABLE",
    },
    "130point": {
        "label": "130 Point",
        "evidence_class": "SALES_RESEARCH_AGGREGATOR",
        "priority": 7,
        "history": "beror på källa/tjänst",
        "best_offer_actual": None,
        "use_for": "Manuell dubbelkontroll när eBay-resultat är tunna eller Best Offer är otydligt.",
        "valuation_role": "CONTEXT_UNTIL_INDIVIDUAL_SALE_VERIFIED",
    },
    "sportscardspro": {
        "label": "SportsCardsPro",
        "evidence_class": "AGGREGATED_PRICE_GUIDE",
        "priority": 8,
        "history": "historiska försäljningar synliga på webbplatsen; API/CSV ger nuvärden, inte historiska sales",
        "best_offer_actual": None,
        "use_for": "Snabb prisnivå, rå/grade-segmentering och sanity check mot annan comp-data.",
        "valuation_role": "SECONDARY_CONTEXT_NOT_DIRECT_SOLD_EVIDENCE",
    },
    "ebay_price_guide": {
        "label": "eBay Price Guide",
        "evidence_class": "AGGREGATED_PRICE_GUIDE",
        "priority": 9,
        "history": "upp till 2 år av completed transactions enligt eBay",
        "best_offer_actual": True,
        "use_for": "Sekundär prisbild och grade-matchad marknadskontext.",
        "valuation_role": "SECONDARY_CONTEXT_NOT_A_SINGLE_COMP",
    },
}


def _clean(value) -> str:
    return " ".join(str(value or "").strip().split())


def exact_identity_query(identity: dict | None) -> str:
    identity = identity or {}
    parts = []
    for key in ("season", "set_name", "player_name"):
        value = _clean(identity.get(key))
        if value:
            parts.append(value)
    card_number = _clean(identity.get("card_number"))
    if card_number:
        parts.append(f"#{card_number.lstrip('#')}")
    parallel = _clean(identity.get("parallel"))
    if parallel:
        parts.append(parallel)
    serial = identity.get("serial_denominator")
    if serial not in (None, "", 0, "0"):
        text = _clean(serial).lstrip("/")
        if text:
            parts.append(f"/{text}")
    grader = _clean(identity.get("grading_company"))
    grade = _clean(identity.get("grade"))
    if grader:
        parts.append(grader)
    if grade:
        parts.append(grade)
    return " ".join(parts)


def ebay_sold_url_for_query(query: str) -> str:
    query = _clean(query)
    if not query:
        return "https://www.ebay.com/sch/i.html?LH_Sold=1&LH_Complete=1"
    return f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(query)}&LH_Sold=1&LH_Complete=1"


def build_comp_research_plan(identity: dict | None) -> dict:
    query = exact_identity_query(identity)
    rows = []
    for key, profile in sorted(SOURCE_PROFILES.items(), key=lambda item: item[1]["priority"]):
        row = {"key": key, **profile}
        row["query"] = query
        if key == "ebay_sold_search":
            row["direct_query_url"] = ebay_sold_url_for_query(query)
        elif key == "tradera_sold":
            row["direct_query_url"] = f"https://www.tradera.com/search?q={quote_plus(query)}" if query else "https://www.tradera.com/"
            row["direct_query_note"] = "Tradera-sökningen kan innehålla aktiva annonser. Endast explicit sålda avslut får registreras som SOLD-comp."
        else:
            row["direct_query_url"] = None
        rows.append(row)
    return {
        "ready": bool(query),
        "query": query,
        "sources": rows,
        "primary_sources": [r for r in rows if r["evidence_class"] in {"DIRECT_REALIZED_SALES", "MULTI_MARKET_SALES_DATABASE"}],
        "secondary_sources": [r for r in rows if r["evidence_class"] == "AGGREGATED_PRICE_GUIDE"],
        "rule": (
            "Exakt verifierade realiserade försäljningar går före prisguider. Prisguider är sanity check och trendkontext, "
            "inte en ersättning för en verifierad exact comp."
        ),
    }
