# FlipFynd v0.12.48 – Comp Source Intelligence

## Fokus
Gör comp-research säkrare och bredare genom att skilja direkt realiserad försäljning från aggregerade prisguider.

## Nytt
- SportsCardsPro tillagt som researchkälla och sekundär sanity check.
- eBay Product Research tillagt som högst prioriterad manuell eBay-källa när exact identity är verifierad.
- Ny `comp_source_intelligence` rangordnar källor efter evidenstyp i stället för varumärke.
- Research-assistenten visar nu rekommenderad ordning: eBay Product Research → eBay Sold → Card Ladder → 130 Point → SportsCardsPro/eBay Price Guide.
- SportsCardsPro API/CSV klassas uttryckligen som current-value data, inte historiska sold comps.
- Manuell snabbregistrering accepterar nu även eBay Product Research och SportsCardsPro som källnamn, men samma strikta sale- och identity-gates gäller.

## Säkerhetsregel
Aggregerade prisguider får aldrig ensamma bli `EXACT_VERIFIED_SOLD`. FlipFynd ska i första hand värdera mot verifierade, realiserade exact sales.
