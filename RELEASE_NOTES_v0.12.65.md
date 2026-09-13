# FlipFynd v0.12.65 — Automatic Comp Research Runner

- Ny en-klicksknapp i evidenskön: **Kör automatisk comp-jakt på topp 5**.
- Kör exact-identity-baserad research på de högst prioriterade korten i stället för hela poolen.
- Skannar befintligt verifierat SOLD-bibliotek automatiskt och visar hur många exact sales som saknas per kort.
- Bygger källspecifika researchlänkar till Tradera, eBay Sold, SportsCardsPro, Card Ladder, Fanatics Collect, COMC och 130 Point.
- Hämtar SportsCardsPro guide/context automatiskt när officiell token finns, men håller guidevärdet strikt utanför SOLD-evidens.
- Fail-closed: ingen scraping, ingen aktiv annons blir SOLD, inget guidevärde blir SOLD och ingen KÖP-signal skapas av research-runnern.
