# FlipFynd v0.6.5 – Sold Comp Import & värderingsintervall

## Varför denna release
v0.6.4 kunde skilja verifierade sålda comps från aktiva asking-priser, men `data/sold_comps.json` var tom och saknade ett säkert importflöde. v0.6.5 gör det möjligt att mata in verkliga avslut utan att FlipFynd behöver gissa försäljningsstatus eller valutakurs.

## Ändrat
- Ny validerad importmotor i `src/sold_comp_import.py`.
- Stöd för CSV och JSON.
- Kräver explicit sålt pris. En avslutad annons blir aldrig automatiskt en försäljning.
- Annan valuta än SEK avvisas om inte importen innehåller explicit SEK-pris eller explicit `fx_rate_to_sek`.
- Provenance, plattform, datum, säljare, sport och URL bevaras när de finns.
- Dubblettskydd med URL eller stabilt fingerprint.
- Ny CLI `import_sold_comps.py` för kontrollerad import till `data/sold_comps.json`.
- Ny administrativ Streamlit-import för CSV/JSON.
- Import av nya comps rensar analyscache så nya marknadsdata faktiskt används.
- Marknadsanalysen beräknar nu observerat Low / Base / High-intervall när minst två jämförbara datapunkter finns.
- I UI visas Low / Base / High som **observerat försäljningsintervall** endast när underlaget är verifierade sålda comps.
- Asking-priser får eget intervall internt men märks uttryckligen som aktiva begärda priser, inte försäljningar.
- Analysresultatet exponerar `comp_valuation_range`.
- Cachemodell uppdaterad till `flip_v5_sold_comp_import_ranges`.
- Synligt versionsnummer: v0.6.5.

## QA som faktiskt körts
- `python -m compileall -q .` – godkänd.
- `python -m unittest discover -s tests -v` – 107/107 tester godkända.
- Separat CLI-smoke-test med en CSV-rad – 1 godkänd och importerad till temporär QA-fil.

## Inte verifierat
- Ingen live-verifiering på `flipfynd.streamlit.app`.
- Ingen live-hämtning av sold-data från eBay, Tradera eller Cardmarket har byggts/verifierats i denna release.
- Streamlit Community Clouds lokala filsystem är inte en permanent databas. Manuellt uppladdade sold comps kan försvinna vid omstart/redeploy om de inte finns i en persistent datakälla.

## Nästa högst värderade steg
Bygg en riktig persistent Sold Comp Collector/Data Store och därefter förbättra comp-matchningen med villkor för grading, serial, condition och källa. En extern collector ska endast lagra försäljningar när källan faktiskt visar att objektet sålts.
