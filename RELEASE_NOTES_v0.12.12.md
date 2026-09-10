# FlipFynd v0.12.12 – Active Supply Intelligence

- Market Gap kan nu manuellt verifieras mot Traderas aktiva search-API.
- Kontroll använder endast strukturerat `player_name`; inga namn gissas från titel.
- Två Tradera-söksidor kontrolleras per användarinitierad verifiering, max tre stöds i modulen.
- Resultaten dedupliceras på Tradera item-id/länk.
- UI visar observerade unika träffar och är tydligt med att detta inte är hela marknadens totalutbud.
- Evidensetiketter: FÅ_OBSERVERADE_TRÄFFAR, BEGRÄNSAT_OBSERVERAT_UTBUD, FLERA_OBSERVERADE_TRÄFFAR, EJ_VERIFIERAT.
- Active Supply Intelligence skapar aldrig KÖP, marknadsvärde eller maxpris.
