# FlipFynd v0.12.73 – Research Candidate Matcher

## Fokus
När query ladder hittar flera möjliga kort ska FlipFynd kunna prioritera sannolik rätt version utan att förväxla kandidatmatchning med verifierad exact identity.

## Nytt
- Ny `src/research_candidate_matcher.py`.
- Matchning väger spelare och kortnummer tyngst, därefter säsong, set/program och parallel.
- Hårda konflikter för fel kortnummer, spelare, säsong, parallel, serienummer, autograf/patch eller grading ger `REJECT`.
- Setnamn kan få delmatch för vanliga titelvariationer men kan aldrig ensam skapa en exact match.
- Automatiska researchpaketet visar rankade lokala kandidat-träffar som **STARK KANDIDAT**, **GRANSKA**, **SVAG** eller **FEL MATCH**.
- UI visar matchade, saknade och konfliktande identitetsfält innan användaren öppnar kandidaten.

## Säkerhetsprincip
Candidate matcher är discovery/research. Den skapar aldrig exact identity, SOLD-evidens, marknadsvärde, maxpris eller KÖP. Premiumvarianter som Rink Collection/autograf/patch får inte blandas ihop med baskort.
