# FlipFynd v0.12.52 – Same-Seller Basket Hunter

## Fokus
När ett kort ser köpvärt ut ska användaren snabbt kunna hitta fler kort från samma säljare och bedöma om flera köp kan dela på frakten.

## Nytt
- Ny knapp på köp-/Top-3-kort: **🧺 Fler kort från samma säljare**.
- Söker igenom den inlästa aktiva Tradera-marknaden efter andra annonser från exakt samma identifierade säljare.
- Redan analyserade annonser visas först, med köpbeslut, fyndpotential och SOLD-underlag när det finns.
- Oanalyserade annonser visas också, men märks tydligt som ännu inte fullanalyserade.
- Användaren kan markera flera kort och få ett transparent **frakt-som-betalas-en-gång-scenario**.
- Scenariot räknar aldrig samfrakt som garanterad; slutlig samfrakt/frakt måste verifieras hos Tradera eller säljaren.
- Fraktmöjlighet får inte göra ett dåligt extrakort till ett bra köp. Varje korts egen värdering/evidens hålls separat.

## QA
- Regressionstest för same-seller filtering, ranking, scenario med känd frakt och fail-safe vid okänd frakt.
