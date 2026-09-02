# FlipFynd v0.7.1 – Likviditetsmotor

## Ändrat
- Ny evidensbaserad säljbarhetsmodell ovanpå tidigare spelar-/setheuristik.
- Verifierade sold comps och deras aktualitet väger tyngre än aktiva annonser.
- Separat räknare för verifierade avslut senaste 30/90 dagar i comp-underlaget.
- Aktiva annonser kan inte ensamma bevisa hög likviditet; asking-only säljbarhet begränsas.
- Saknad sold-data tolkas som osäkerhet, inte automatiskt som svårsålt.
- Resultatkort visar nu Säljbarhet: Mycket lättsålt / Lättsålt / Normalt / Trögsålt / Svårsålt.
- Fyndpoängen använder den förbättrade likviditeten.
- Cachemodell höjd till flip_v10_liquidity_evidence.

## Viktig begränsning
Sold-comp-bibliotekets täckning avgör hur datadriven säljbarheten kan bli. Modellen hittar inte på försäljningsfrekvens när historiska avslut saknas.

## QA
- python -m compileall -q .: godkänd
- python -m unittest discover -s tests -p 'test_*.py': 147/147 tester godkända
- Ingen live-verifiering av Streamlit/Tradera utförd.
