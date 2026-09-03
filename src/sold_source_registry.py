"""Auditable registry of sold-data sources for FlipFynd.

The registry deliberately separates a useful research destination from a source
that FlipFynd can ingest automatically. A website being able to show sold comps
does not imply that a stable/public API exists or that FlipFynd may scrape it.
"""
from __future__ import annotations

SOURCES = (
    {
        "key": "ebay_sold_search",
        "label": "eBay Sold",
        "research_url": "https://www.ebay.com/sch/i.html?LH_Sold=1&LH_Complete=1",
        "supports_sports_cards": True,
        "automated_ingestion": False,
        "status": "RESEARCH_ONLY",
        "note": "Bra primär kontrollkälla. FlipFynd importerar inte sidan automatiskt utan verifierbar integrationsväg.",
    },
    {
        "key": "ebay_price_guide",
        "label": "eBay Price Guide",
        "research_url": "https://pages.ebay.com/price-guide/",
        "supports_sports_cards": True,
        "automated_ingestion": False,
        "status": "RESEARCH_ONLY",
        "note": "eBay visar historiska trading-card-försäljningar, men FlipFynd behandlar inte webbgränssnittet som ett API.",
    },
    {
        "key": "130point",
        "label": "130 Point",
        "research_url": "https://130point.com/",
        "supports_sports_cards": True,
        "automated_ingestion": False,
        "status": "RESEARCH_ONLY",
        "note": "Användbar manuell kontrollkälla. Ingen officiell publik utvecklarintegration antas av FlipFynd.",
    },
    {
        "key": "card_ladder",
        "label": "Card Ladder",
        "research_url": "https://cardladder.com/",
        "supports_sports_cards": True,
        "automated_ingestion": False,
        "status": "RESEARCH_ONLY",
        "note": "Bred historisk marknadsdata; eventuell framtida integration kräver verifierade villkor och teknisk åtkomst.",
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
