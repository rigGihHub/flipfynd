# FlipFynd v0.11.26 – Action-First Result Cards

## Varför
Resultatkorten hade blivit för informationsrika. Samma signaler visades både i beslutshuvudet och längre ned, vilket gjorde det svårare att snabbt svara på kärnfrågan: ska kortet köpas, bevakas eller hoppas över – och till vilket maxpris?

## Ändrat
- Resultatkortets första nivå fokuserar på beslut, totalpris, realistiskt värde, möjlig nettovinst, säljbarhet, tre korta varför-skäl och maxpris.
- Dubblerade metrics för totalpris/nettovinst har tagits bort från primärvyn.
- Riskpoäng, värderingssäkerhet, spelar-ID, Exact Identity Gate-poäng, Flip Velocity och övrig diagnostik ligger kvar i den fulla analysen i stället för att konkurrera om uppmärksamheten.
- Okänd frakt och auktionsbuffert visas fortfarande direkt eftersom de kan ändra köpbeslutet.
- Informationsövertag visas fortfarande direkt, men uttryckligen som researchsignal.
- Den fulla analysen finns kvar bakom “Visa hela analysen och underlaget”.

## Säkerhet
Ingen analys-, värderings-, ranking- eller köpgräns har ändrats i denna release. Detta är en UX-förenkling av hur redan beräknade resultat presenteras.
