# FlipFynd v0.11.31 – Outcome Review

## Fokus
Ge FlipFynd explicit, användarverifierad information om varför en verklig affär avvek från prognosen utan att appen gissar orsaken.

## Nytt
- Outcome Review på avslutade journalposter.
- Verifierade orsaker kan markeras: fel identitet, fel variant/parallel, sämre skick, marknadsfall, svagare efterfrågan, försäljningsannons, högre kostnader, frakt/logistik eller annan verifierad orsak.
- Valfri fri kommentar till varje review.
- Miss Analysis tar nu med manuella orsaker separat från automatiskt härledda pris-/vinst-/tidsmissar.
- Identitetsmiss bedöms endast när användaren uttryckligen har markerat fel kortidentifiering.
- Okända/ogiltiga review-koder ignoreras.
- Journalens schema höjt till version 2 med bakåtkompatibla nya fält.

## Säkerhetsprincip
Outcome Review ändrar inga modellvikter automatiskt. Manuella orsaker används endast när de uttryckligen registrerats av användaren.

## QA
- 381 tester passerade.
- compileall passerade.
- Live Streamlit är inte verifierad/deployad.
