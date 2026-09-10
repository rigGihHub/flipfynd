# FlipFynd v0.12.24 – Market Coverage Autopilot

- Ny `market_coverage_autopilot.py` väljer automatiskt rätt nästa marknadsåtgärd.
- Om någon marknad är stale/due prioriteras först en gemensam incremental refresh för hockey + fotboll.
- Om marknaderna är färska men ofullständiga fortsätter FlipFynd automatiskt med nästa market batch för båda sporterna i samma körning.
- När båda är färska och kompletta visas bara att marknaden är redo.
- Huvudvyn har nu en enda intelligent marknadsknapp i stället för att användaren först behöver förstå refresh vs market batch.
- Avancerad marknadshämtning finns kvar som reservverktyg, men UI säger uttryckligen att den normalt inte behövs.
- Marknadsstatus-texten hänvisar inte längre användaren till avancerade inställningar för att bygga täckning.
- Ingen ranking-, värderings-, KÖP-, maxpris- eller risklogik ändras.
