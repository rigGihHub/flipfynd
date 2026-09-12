"""Auditable registry of sold-data sources for FlipFynd.

The registry deliberately separates a useful research destination from a source
that FlipFynd can ingest automatically. A website being able to show sold comps
does not imply that a stable/public API exists or that FlipFynd may scrape it.
"""
from __future__ import annotations

SOURCES = (
    {
        "key": "ebay_product_research",
        "label": "eBay Product Research",
        "research_url": "https://www.ebay.com/sh/research",
        "supports_sports_cards": True,
        "automated_ingestion": False,
        "status": "RESEARCH_ONLY",
        "evidence_type": "DIRECT_REALIZED_SALES",
        "note": "Officiell eBay-research med upp till 3 års försäljningsdata och faktiskt accepted Best Offer-pris. Kräver manuell research/inloggning; inget webb-UI skrapas.",
    },
    {
        "key": "ebay_sold_search",
        "label": "eBay Sold",
        "research_url": "https://www.ebay.com/sch/i.html?LH_Sold=1&LH_Complete=1",
        "supports_sports_cards": True,
        "automated_ingestion": False,
        "status": "RESEARCH_ONLY",
        "evidence_type": "DIRECT_REALIZED_SALES",
        "note": "Bra primär kontrollkälla för färska avslut. Regular sold search är kortare historik än Product Research och kan dölja accepted Best Offer-priset.",
    },
    {
        "key": "ebay_price_guide",
        "label": "eBay Price Guide",
        "research_url": "https://pages.ebay.com/price-guide/",
        "supports_sports_cards": True,
        "automated_ingestion": False,
        "status": "RESEARCH_ONLY",
        "evidence_type": "AGGREGATED_PRICE_GUIDE",
        "note": "Sekundär prisguide byggd på completed sales; uppges använda accepted Best Offer och upp till två års transaktioner. Inte en enskild exact sold comp.",
    },
    {
        "key": "130point",
        "label": "130 Point",
        "research_url": "https://130point.com/",
        "supports_sports_cards": True,
        "automated_ingestion": False,
        "status": "RESEARCH_ONLY",
        "evidence_type": "SALES_RESEARCH_AGGREGATOR",
        "note": "Användbar manuell dubbelkontroll av sales. FlipFynd antar ingen officiell publik utvecklarintegration och räknar inte ett visat riktpris som exact comp.",
    },
    {
        "key": "sportscardspro",
        "label": "SportsCardsPro",
        "research_url": "https://www.sportscardspro.com/",
        "supports_sports_cards": True,
        "automated_ingestion": False,
        "status": "RESEARCH_ONLY",
        "evidence_type": "AGGREGATED_PRICE_GUIDE",
        "note": "Dagligen uppdaterad prisguide byggd av eBay- och Marketplace-sales. Bra sanity check; API/CSV ger aktuella värden men inte historiska sales och får därför inte behandlas som direct sold comps.",
    },
    {
        "key": "card_ladder",
        "label": "Card Ladder",
        "research_url": "https://cardladder.com/",
        "supports_sports_cards": True,
        "automated_ingestion": False,
        "status": "RESEARCH_ONLY",
        "evidence_type": "MULTI_MARKET_SALES_DATABASE",
        "note": "Bred historisk sales-databas från flera marknadsplatser. Enskilda verifierbara sales kan vara stark evidens; automatisk integration kräver verifierad åtkomst/licens.",
    },
)


def sold_source_registry() -> list[dict]:
    return [dict(source) for source in SOURCES]


def ingestion_ready_sources() -> list[dict]:
    return [source for source in sold_source_registry() if source["automated_ingestion"]]


def research_only_sources() -> list[dict]:
    return [source for source in sold_source_registry() if not source["automated_ingestion"]]


def source_readiness_summary() -> dict:
    sources = sold_source_registry()
    ready = ingestion_ready_sources()
    return {
        "source_count": len(sources),
        "automated_count": len(ready),
        "research_only_count": len(sources) - len(ready),
        "status": "AUTOMATION_READY" if ready else "MANUAL_RESEARCH_REQUIRED",
    }
