# FlipFynd v0.12.43 – Checklist, Case-Hit & Short-Print Evidence Engine

## Fokus
Gör FlipFynd bättre på att förstå skillnaden mellan checklistkunskap, objektivt verifierad knapphet, officiellt chase-språk och lösa marketplace-termer som "SSP" och "case hit".

## Nytt
- Ny `src/rarity_evidence.py`.
- Separat evidensgradering för:
  - verifierad serienumrering /N,
  - publicerade packodds,
  - källstyrd case-hit/case-pull-signal,
  - källstyrd SSP/short-print-signal,
  - officiellt chase-program där exakt sällsynthet fortfarande är okänd,
  - okällstyrda SSP/case-hit-påståenden.
- 2025-26 Upper Deck Series 1/2 kunskap uppdaterad med direkt officiell checklistkälla.
- Young Guns Clear Cut bär nu publicerade 1:144 Hobby-odds i kunskapsmodellen.
- Outburst Red Young Guns /25 och Outburst Gold Young Guns 1/1 fortsätter som objektivt dokumenterade print-run-strukturer.
- 2025-26 Topps UEFA Club Competitions har lagts till som aktuell officiell källa. Roots, Born Champ och 8Bit-programmen markeras som officiella chase-program men uppgraderas **inte** automatiskt till SSP/case hit utan odds/starkare källstöd.

## Säkerhetsprincip
"Case hit", "SSP" och "short print" är inte värden. FlipFynd ska först fråga: vem säger det, finns publicerade odds, finns serienumrering, och gäller uppgiften exakt den här versionen?

## QA
- Nya regressionstester för objektiv raritet, packodds, okällstyrd case-hit-term och konservativ chase-klassning.
