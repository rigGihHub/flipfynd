# FlipFynd v0.12.56 – Comp Acquisition Router

## Fokus
Gör comp-inhämtningen mer målinriktad. FlipFynd ska inte söka samma källa om och om igen när det egentligen saknas lokal svensk evidens eller oberoende källspridning.

## Nytt
- Ny `comp_acquisition_router` som granskar redan verifierade exact SOLD och väljer nästa bästa researchkälla.
- Tradera prioriteras när svensk exact SOLD saknas.
- eBay prioriteras när internationell exact SOLD saknas eller underlaget är tunnare än två sales.
- Oberoende källa, t.ex. Card Ladder/Fanatics/COMC, prioriteras när all evidens kommer från samma marknad.
- Ny **Källquorum**: minst två exact SOLD från minst två källgrupper. Detta är ett researchkvalitetsmått och skapar inte KÖP eller marknadsvärde.
- Research-assistenten visar nu tydligt nästa rekommenderade källa och direktknapp när en exakt söklänk finns.

## Tradera
Tradera v4-dokumentationen visar app-autentiserad sökning och seller-item-endpoints, men aktiva/avslutade annonser får fortfarande inte tolkas som SOLD utan explicit sale-evidens. FlipFynd håller därför den hårda SOLD-gaten intakt.

## Säkerhetsprincip
Aktiva annonser är utbud, inte comps. Prisguider är kontext, inte individuella sales. Källquorum är kvalitetskontroll, inte en köpsignal.
