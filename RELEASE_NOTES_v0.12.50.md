# FlipFynd v0.12.50 – Blocker Normalisation & Decision Readiness

## Problem som fixas
Hundratals dynamiska stopporsaker (t.ex. olika procentsatser för analyssäkerhet och konservativt scenario) grupperades tidigare som `Övrigt`, vilket gjorde diagnostiken nästan oanvändbar.

## Nytt
- Dynamiska procent-, pris- och tröskelvärden normaliseras innan kategorisering.
- `Analyssäkerhet X%` grupperas nu under **För låg analyssäkerhet**.
- `Konservativt scenario ... av inköpskostnaden` grupperas under **För svag värderingsmarginal**.
- Fler stabila blockerfamiljer för identitet, SOLD/prisunderlag, marginal, säljbarhet, skick och risk.
- Exakta stopporsaker finns kvar och visas med sin normaliserade kategori; ingen evidens kastas bort.
- Ny **Beslutsunderlag – var saknas evidens?** visar antal/andel analyserade annonser med sökbar exakt identitet, minst en användbar SOLD, säker värdering, tillräcklig analyssäkerhet och KÖP.

## Princip
Diagnostiken förändrar aldrig ranking, värdering, maxbud eller köpbeslut. Den sammanfattar endast redan beräknade fakta.
