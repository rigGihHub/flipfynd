# FlipFynd v0.12.08 – Operational Search Expansion

- Search Expansion kan nu köras mot Traderas officiella read-only REST v4 `/v4/search` när `TRADERA_APP_ID` och `TRADERA_APP_KEY` finns.
- App credentials skickas som `X-App-Id` och `X-App-Key`; ingen user-token, köp- eller budfunktion används.
- Upp till 12 av den befintliga säkra Search Expansion-planens sökvägar körs per användarinitierad körning.
- API-svaret parsas fail-closed. Endast strukturerade resultat med explicit item-id och titel släpps in som kandidater.
- Pris används endast om Tradera uttryckligen returnerar ett prisfält. Frakt gissas inte i API-adaptern.
- API-träffar sparas separat i `data/search_expansion_items.json`, dedupliceras på Tradera item-id och slås ihop med ordinarie aktiva annonser vid inläsning.
- Alla API-träffar går därefter genom samma ordinarie FlipFynd-analys. Search Expansion skapar fortfarande aldrig identitet, marknadsvärde, maxpris eller KÖP.
- Ny knapp i novice-vyn: **Kör Search Expansion nu**. Den visas funktionellt först när säkra Tradera app credentials kan lösas från miljö eller Streamlit secrets.
- Integrationen är read-only search/discovery och implementerar inte automatiserade bud, köp eller sniping.
- REST v4 är beta, därför är parsningen av SearchResult medvetet defensiv och okända svarsscheman avvisas istället för att tolkas fritt.
