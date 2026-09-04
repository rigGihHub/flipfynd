# FlipFynd v0.11.37 – False Positive Review

## Syfte
Göra verkliga dåliga KÖP-rekommendationer synliga som ett eget granskningsunderlag, utan att låta små datamängder eller efterhandsantaganden ändra modellen.

## Nytt
- Ny `src/false_positive_review.py`.
- Endast avslutade journalposter som hade KÖP-rekommendation är kvalificerade.
- Falskt positivt utfall kräver faktisk förlust eller en stor dokumenterad miss mot förväntad nettovinst.
- Små prognosavvikelser ignoreras.
- Segmentering på fyndscore, sport och befintliga edge/hunter-signaler.
- Minst 5 avslutade KÖP krävs för mönstergranskning; varje segment behöver också minst 5 egna utfall.
- Ny UI-panel i Flip Journal.
- Ingen automatisk ändring av score, beslut eller modellvikter.

## Viktig avgränsning
Panelen säger var falskt positiva utfall samlas. Den påstår inte varför affären gick dåligt. Orsaker hör fortsatt hemma i Outcome Review och Miss Analysis.
