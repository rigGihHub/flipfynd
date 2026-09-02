# FlipFynd v0.9.1 – Visual Card Detective

## Nytt
- Visual Edge-kön får en manuell **Analysera bilden**-knapp.
- En separat visionmodul kan, när `OPENAI_API_KEY` finns, granska högst två annonsbilder.
- Modellen får bara lämna försiktiga hypoteser om synliga detaljer: spelare, set/produkt, år/säsong, kortnummer, serienummer, parallel/variant, rookie-markering, autograf, patch/relic samt grading.
- Bildhypoteser jämförs mot rubrik/annonstext och märks som:
  - möjlig visuell edge,
  - konflikt – verifiera,
  - låg säkerhet – verifiera manuellt,
  - ingen tydlig ny information.
- UI visar visuella upptäckter, konflikter, ledtrådar och osäkerheter direkt vid annonsen.

## Säkerhet
- Bildmodellen får inget schemafält för pris, värde, ROI, vinst, maxbud eller köprekommendation.
- Bildresultat är alltid `safe_for_valuation = false` i v0.9.1.
- Visual Card Detective påverkar inte automatiskt värdering, Fyndpoäng, beslut eller maxbud.
- Låg bildsäkerhet kan aldrig presenteras som en säker visuell edge.

## Drift
- Automatisk bildtolkning kräver `OPENAI_API_KEY` i appens miljö/Streamlit secrets.
- Utan nyckel fungerar Visual Edge fortfarande som prioriterad manuell granskningskö.
