# FlipFynd v0.12.17 – Market Pressure Monitor

- Ny `src/market_pressure_monitor.py`.
- Visar tre faktiska serier sida vid sida för samma exakta kortidentitet: Exact Supply History, verifierade exakta SOLD och realiserade SOLD-priser.
- SOLD-pris använder endast verifierade exact-ready försäljningar och priser som redan normaliserats till SEK av sold-intaget.
- Prisriktning kräver minst tre daterade verifierade exakta SOLD inom perioden mellan första och senaste supply-snapshot.
- Prisriktningen jämför medianen i den tidigare delen med medianen i den senare delen: `HÖGRE_OBSERVERAT_SOLD_PRIS`, `LÄGRE_OBSERVERAT_SOLD_PRIS` eller `OFÖRÄNDRAT_OBSERVERAT_SOLD_PRIS`.
- Färre än tre försäljningar ger `EJ_BEDÖMBAR`.
- Prisriktningen kallas uttryckligen observerad SOLD-prisriktning och är inte en generell marknadstrend.
- Ingen demand-signal, scarcity-score, marknadstrend, värdering, maxpris eller KÖP skapas.
- Exact Card Supply-vyn visar nu ett kompakt block `Market Pressure – observerade fakta` när underlaget finns.
