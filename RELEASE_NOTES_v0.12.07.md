# FlipFynd v0.12.07 – Search Expansion Engine

- Ny `src/search_expansion.py` bygger alternativa Tradera-sökvägar från redan strukturerad FlipFynd-evidens.
- Sökvarianter kan omfatta exakt spelarnamn, efternamn, diakritikfri variant, spelare + set/program, spelare + set + säsong samt rookie-term endast när en befintlig rookie-signal redan finns.
- Inga stavfel, nya spelare, varianter eller rookiestatusar hittas på av sökmotorn.
- Varje säker query expanderas över Traderas dokumenterade söksorteringar `Relevance`, `PriceAscending` och `EndDateAscending`.
- Hockey använder kategori 293316 och fotboll 293311.
- Sökplanen väljer upp till sex spelare med befintlig, icke-låg spelaridentifiering och skapar högst 36 sökvägar per körning.
- Ny novice-expander **Search Expansion – fler sökvägar till fynd** visar de viktigaste sökvägarna och om Tradera API är säkert konfigurerat.
- Automatisk API-sökning aktiveras inte utan `TRADERA_APP_ID` och `TRADERA_APP_KEY`; motorn failar stängt.
- Legacy `fetch_data.py` är sanerad: hårdkodad placeholder-nyckel är borttagen och parametrarna är uppdaterade till Traderas dokumenterade v3 SearchService-kontrakt: `query`, `categoryId`, `pageNumber`, `orderBy`.
- Search Expansion skapar endast kandidatsökningar. Alla träffar måste fortfarande passera ordinarie identitets-, sold-, värderings-, risk- och KÖP-regler.
- Ingen KÖP-, värderings-, maxpris-, sold-, risk- eller slutlig rankinglogik ändras.
