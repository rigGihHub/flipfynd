# FlipFynd v0.12.27 – Autopilot deploy compatibility fix

- Fixar kraschen i marknadsstatusen när Streamlit Cloud under en deploy råkar köra nya `app.py` mot en äldre cache/import av `market_coverage_autopilot.py`.
- Huvudanropet använder fortfarande v0.12.25+ `analyzed_results` och därmed Coverage Gap Planner när rätt modul är laddad.
- Om just keyword-argumentet `analyzed_results` inte stöds faller appen tillfälligt tillbaka till den äldre fyrarguments-signaturen i stället för att krascha.
- Andra TypeError-fel fångas inte utan kastas vidare, så riktiga programmeringsfel maskeras inte.
- Ingen ranking-, värderings-, KÖP-, maxpris-, risk- eller segmentlogik ändras.
