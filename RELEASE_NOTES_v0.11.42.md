# FlipFynd v0.11.42 – Capital Efficiency

## Varför
FlipFynd ska prioritera hur bra ett fynd använder verkligt kapital, inte bara största nominella vinst.

## Nytt
- Ny `capital_efficiency` per analyserat kort.
- Väver ihop nettovinst, verifierad säljtakt, säljchans, säljbarhet, kapitalbindning och realistisk nedsida.
- Visar vinst per 30 dagar och ROI per 30 dagar.
- Straffar tydlig nedsida.
- Avstår helt från poäng när verifierad sold-baserad säljtakt saknas.
- Kort kapitalrad i huvudresultatet; detaljerna ligger kvar i analysen.

## Säkerhetsprincip
Ingen heuristisk eller aktiv-listing-baserad säljtakt får skapa en exakt kapitalpoäng. Identitets- och comp-grindarna ändras inte. Modellen ändrar inte köpbeslut automatiskt i denna release.

## Nästa steg
Validera Capital Efficiency mot riktiga Flip Journal-utfall innan den får styra huvudrankingen.
