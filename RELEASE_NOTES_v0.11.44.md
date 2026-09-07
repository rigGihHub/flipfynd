# FlipFynd v0.11.44 – Flip Journal Validation

## Mål
Mäta om Capital Efficiency faktiskt fungerar på riktiga avslut innan signalen får större makt i ranking eller budgetfördelning.

## Nytt
- Flip Journal schema v4.
- Nya köp sparar Capital Efficiency-poäng, label, vinst/30 dagar, ROI/30 dagar och beräknad nedsida vid köptillfället.
- Äldre journalposter utan signal fylls aldrig i retroaktivt.
- Ny valideringspanel jämför verkliga avslut med kapitalpoäng 65–100 mot 0–64.
- Visar verklig win rate, medianvinst per 30 dagar och median säljtid.
- Minst 5 avslut per grupp krävs innan riktningen jämförs.
- Minst 20 relevanta avslut totalt krävs innan manuell modellgranskning rekommenderas.
- Inga automatiska viktändringar.

## Varför
FlipFynd ska inte anta att en ny rankingidé är bra bara för att den verkar logisk. Den ska bevisas mot riktiga köp och försäljningar.

## Nästa steg
När tillräckligt många riktiga avslut finns: granska kalibreringen och först därefter avgöra om Capital Efficiency ska få påverka huvudrankingen mer.
