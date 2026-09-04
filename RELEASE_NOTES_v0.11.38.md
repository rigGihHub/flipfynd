# FlipFynd v0.11.38 – False Negative Review

## Syfte
Mäta om FlipFynd blivit så försiktigt att lönsamma fynd missas.

## Nytt
- Ny `src/false_negative_review.py`.
- Endast verkligt avslutade affärer som **inte** hade KÖP-rekommendation analyseras.
- Ett missat starkt fynd kräver konservativt minst **100 kr faktisk nettovinst** och **25 % faktisk ROI**.
- Öppna/osålda affärer räknas aldrig som missade fynd.
- Minst 5 relevanta avslut krävs innan mönster visas.
- Segmentering på ursprungligt beslut, fyndscore, värderingssäkerhet, risk, säljbarhet, sold-comp-läge, edge/hunter-signaler och säkerhets-/konfliktnedgraderingar när dessa data finns.
- Flip Journal sparar nu fler beslutssignaler vid fångst så framtida utfall kan kopplas till de faktiska säkerhetslagren.
- Ny UI-panel bredvid False Positive Review.
- Ingen automatisk ändring av score, beslut eller modellvikter.

## Viktig avgränsning
Ett lönsamt utfall bevisar inte att en säkerhetsregel var fel. Panelen visar återkommande kandidater för manuell modellgranskning först när verkliga utfall finns.
