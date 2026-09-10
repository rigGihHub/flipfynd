# FlipFynd v0.11.93 – Finding Funnel Diagnostic

- Ny tydlig diagnostik direkt i nybörjarvyn: **Varför hittar FlipFynd så få kort?**
- Visar hela tratten:
  - inlästa annonser
  - rätt sport
  - giltigt pris
  - inom budget
  - matchar sökning
  - rätt annonsform
  - efter specialfilter
  - analyserade
- Visar antal **KÖP / BEVAKA / SKIP**.
- Visar största bortfallet i grundsållningen.
- Summerar vanligaste stopporsaker för analyserade kort utifrån befintliga `decision_diagnostics`.
- Exakta stopporsaker kan öppnas separat.
- Om 0 kort når analysen förklarar appen att problemet ligger i filter/data före beslutsmotorn.
- Om kort når analysen men KÖP = 0 förklarar appen att underlag/ekonomi stoppar köpbeslut.
- Topp 3 “Bästa tillgängliga” finns kvar även när inget är KÖP.
- Ingen köp-, ranking-, värderings-, maxpris- eller tröskellogik ändras.
