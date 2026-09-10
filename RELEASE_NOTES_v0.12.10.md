# FlipFynd v0.12.10 – Market Sweep Engine

- Ny `src/market_sweep_engine.py` sveper hela den redan inlästa kandidatpoolen genom flera marknadslinser.
- Linser: billigaste kvartilen i aktuell sökning, nyaste Tradera-sidorna, slutar snart, dåligt beskriven annons, lot/paket, Lot Treasure, rookie/prospect, variantstruktur, Search Expansion-träffar och market-attention.
- Billigaste kvartilen är relativ till aktuell sökning och betyder inte att kortet är undervärderat.
- `newest-pages` bygger på att Tradera-crawlern börjar från låga sidnummer; det är en färskhetslins, inte en exakt tidsstämpel.
- Om första fullanalysen inte hittar KÖP får Market Sweep nu första chansen att välja upp till 8 förbisedda kandidater för full analys innan Discovery Engine och vanlig fallback.
- Total hard cap för andra passet är fortfarande 45 fullanalyserade kandidater.
- Max två kandidater per spelare i sweep-fasen för bättre marknadsbredd.
- Ingen ny fyndscore, kortidentitet, marknadsvärdering, maxpris, risk eller KÖP-logik skapas.
