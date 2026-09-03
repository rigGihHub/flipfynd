# FlipFynd v0.11.19 – Sold Source Readiness

## Varför denna release
v0.11.18 skapade ett säkert adapterlager, men en adapter är inte samma sak som en verkligt ansluten extern sold-källa. v0.11.19 gör den skillnaden synlig och förhindrar att appen ger ett falskt intryck av live-comps.

## Nytt
- Ny **Sold Source Readiness** i Administration & data.
- Register över eBay Sold, eBay Price Guide, 130 Point och Card Ladder som research-källor.
- Tydlig separat status för `RESEARCH_ONLY` kontra verkligt automatiserad ingestion.
- Appen visar uttryckligen när antalet automatiskt anslutna externa sold-källor är 0.
- Research-länkar gör det snabbare att kontrollera comps manuellt utan att försvaga värderingsgrindarna.

## Säkerhetsprincip
Att en webbplats visar sold-data betyder inte att FlipFynd har rätt eller teknisk möjlighet att läsa den automatiskt. Ingen scraping eller inofficiell integration läggs in bara för att öka mängden data.

## Nästa steg
Verifiera en stabil och tillåten integrationsväg för faktisk sold-data. Först därefter ska en källa få status som automatiskt ansluten.
