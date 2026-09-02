# FlipFynd v0.5.1 – robust live-hämtning

## Fixat
- Traderaannonser sparas nu löpande efter varje lyckad resultatsida i stället för först när en hel sport är färdighämtad.
- Live-progress skrivs till `tradera_fetch_state.json` efter varje sida: aktiv sport, sida, antal lästa annonser och antal nya annonser.
- Streamlit läser om analysunderlaget under pågående hämtning så nya annonser och sportfördelningen blir synliga utan att hela crawlen måste bli klar först.
- Statusraden visar t.ex. `Hämtar Hockey: sida 14 • 612 annonser lästa • 83 nya` och därefter `Hockey klar ✓ • Hämtar Fotboll...`.
- Administration & data visar aktuell progress per sport.
- Varje Tradera-sida har 45 sekunders navigeringstimeout. Ett sidfel stoppar aktuell crawl i stället för att låta processen hänga genom många sidor.

## QA
- 39/39 unittester godkända, inklusive nya tester för progress-state och löpande persistens.
- `python -m compileall -q .` godkänd.
- Livebeteende mot Tradera/Streamlit Community Cloud är inte verifierat i denna arbetsmiljö och behöver kontrolleras efter framtida push.
