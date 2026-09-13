# FlipFynd v0.12.70 – Research Player Recovery

- Adds a research-only player recovery pass for structured marketplace titles.
- Prefers the two lexical tokens immediately after an explicit checklist number, a common Tradera/eBay convention.
- Supports player-first titles by examining only the prefix before the season/set.
- Rejects common team names, colours, product words and listing boilerplate so they do not become invented players.
- Recovered names may unlock narrow research queries only; they never unlock exact SOLD, valuation, max price or BUY without the strict exact-identity gate.
