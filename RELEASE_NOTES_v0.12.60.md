# FlipFynd v0.12.60 – Decision Tier Runtime Compatibility Hotfix

- Fixar Streamlit-runtimefelet där `app.py` skickar `require_verified_economic_edge=True` till en äldre/stale `build_decision_tiers`-signatur.
- Ny kompatibilitetswrapper känner av funktionssignaturen och använder den nya parametern när den finns.
- Vid partiell/stale deploy förfiltreras kandidater med samma hårda krav på exact identity, minst 2 SOLD, verifieringsbart marknadsvärde, KÖP-signal och kostnad under evidensbaserat maxpris.
- Ingen återgång till den gamla, för snälla Top-3-rankningen.
