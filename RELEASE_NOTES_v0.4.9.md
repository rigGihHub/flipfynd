# FlipFynd v0.4.9 – Statistik, auktionskostnad och kalibreringsdiagnostik

## Förbättringar
- Versionsnummer uppdaterat till v0.4.9.
- Startsidan visar nu senaste kända hämtningstid när fetch-metadata finns.
- Om äldre data saknar fetch-metadata visas i stället när datafilen senast ändrades, så UI:t inte missvisande visar "Aldrig" trots att analysunderlaget finns.
- Auktionskort visar tydlig skillnad mellan aktuellt pris inkl. frakt och den konservativa kostnad som används i fyndkalkylen.
- Auktionsbufferten visas direkt i fyndkortet.
- SKIP/KANSKE-kort får en expander "Varför når kortet inte KÖP?" som visar vilka konkreta KÖP-trösklar som missas, t.ex. nettovinst, ROI, säljchans, riskjusterad vinst, downside eller analyssäkerhet.
- Analysresultatet exponerar nu försäljningsform och beslutsdiagnostik till UI:t.

## QA
- 36/36 unittest-tester godkända.
- `python -m compileall -q .` godkänd.
- Livebeteende på Streamlit/Tradera behöver verifieras efter deploy.
